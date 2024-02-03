import builtins
from json import JSONDecodeError
import os

import pytest
from unittest.mock import call, patch, Mock
from dotenv import load_dotenv
from jsonschema import ValidationError
from const.function_calls import ARCHITECTURE, DEVELOPMENT_PLAN
from helpers.AgentConvo import AgentConvo
from helpers.Project import Project
from helpers.agents.Architect import Architect
from helpers.agents.TechLead import TechLead
from utils.function_calling import parse_agent_response, FunctionType
from test.test_utils import assert_non_empty_string
from test.mock_questionary import MockQuestionary
from utils.llm_connection import create_gpt_chat_completion, stream_gpt_completion, \
    assert_json_response, assert_json_schema, clean_json_response, retry_on_exception
from main import get_custom_print

load_dotenv()
os.environ.pop("AUTOFIX_FILE_PATHS", None)


def test_clean_json_response_True_False():
    # Given a JSON response with Title Case True and False
    response = '''
```json
{
    "steps": [
        {
            "type": "command",
            "command": {
                "command": "git init",
                "daemon": False,
                "timeout": 3000,
                "boolean": False
            },
            "another_True": True,
            "check_if_fixed": True
        }
    ]
}
```
'''

    # When
    response = clean_json_response(response)

    # Then the markdown is removed
    assert response.startswith('{')
    assert response.endswith('}')
    # And the booleans are converted to lowercase
    assert '"daemon":false,' in response
    assert '"boolean":false' in response
    assert '"another_True":true,' in response
    assert '"check_if_fixed":true' in response


def test_clean_json_response_boolean_in_python():
    # Given a JSON response with Python booleans in a content string
    response = '''
{
    "type": "code_change",
    "code_change": {
        "name": "main.py",
        "path": "./main.py",
        "content": "json = {'is_true': True,\\n 'is_false': False}"
    }
}'''

    # When
    response = clean_json_response(response)

    # Then the content string is left untouched
    assert '"content": "json = {\'is_true\': True,\\n \'is_false\': False}"' in response


@patch('utils.llm_connection.styled_text', return_value='')
class TestRetryOnException:
    def setup_method(self):
        self.function: FunctionType = {
            'name': 'test',
            'description': 'test schema',
            'parameters': {
                'type': 'object',
                'properties': {
                    'foo': {'type': 'string'},
                    'boolean': {'type': 'boolean'},
                    'items': {'type': 'array'}
                },
                'required': ['foo']
            }
        }

    def _create_wrapped_function(self, json_responses: list[str]):
        project = Project({'app_id': 'test-app'})
        args = {}, 'test', project

        def retryable_assert_json_schema(data, _req_type, _project):
            json_string = json_responses.pop(0)
            if 'function_buffer' in data:
                json_string = data['function_buffer'] + json_string
            assert_json_schema(json_string, [self.function])
            return json_string

        return retry_on_exception(retryable_assert_json_schema), args

    def test_incomplete_value_string(self, mock_styled_text):
        # Given incomplete JSON
        wrapper, args = self._create_wrapped_function(['{"foo": "bar', '"}'])

        # When
        response = wrapper(*args)

        # Then should tell the LLM the JSON response is incomplete and to continue
        # 'Unterminated string starting at'
        assert response == '{"foo": "bar"}'
        assert 'function_error' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 0

    def test_incomplete_key(self, mock_styled_text):
        # Given invalid JSON boolean
        wrapper, args = self._create_wrapped_function([
            '{"foo',
            '": "bar"}'
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM the JSON response is incomplete and to continue
        # 'Unterminated string starting at: line 1 column 2 (char 1)'
        assert response == '{"foo": "bar"}'
        assert 'function_error' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 0

    def test_incomplete_value_missing(self, mock_styled_text):
        # Given invalid JSON boolean
        wrapper, args = self._create_wrapped_function([
            '{"foo":',
            ' "bar"}'
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM the JSON response is incomplete and to continue
        # 'Expecting value: line 1 column 8 (char 7)'
        assert response == '{"foo": "bar"}'
        assert 'function_error' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 0

    def test_invalid_boolean(self, mock_styled_text):
        # Given invalid JSON boolean
        wrapper, args = self._create_wrapped_function([
            '{"foo": "bar", "boolean": True}',
            '{"foo": "bar", "boolean": True}',
            '{"foo": "bar", "boolean": True}',
            '{"foo": "bar", "boolean": true}',
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM there is an error in the JSON response
        # 'Expecting value: line 1 column 13 (char 12)'
        assert response == '{"foo": "bar", "boolean": true}'
        assert args[0]['function_error'] == 'Invalid value: `True`'
        assert 'function_buffer' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 1

    def test_invalid_escape(self, mock_styled_text):
        # Given invalid JSON boolean
        wrapper, args = self._create_wrapped_function([
            '{"foo": "\\!"}',
            '{"foo": "\\xBADU"}',
            '{"foo": "\\xd800"}',
            '{"foo": "bar"}',
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM there is an error in the JSON response
        # 'Invalid \\escape: line 1 column 10 (char 9)'
        assert response == '{"foo": "bar"}'
        assert len(args[0]['function_error']) > 0
        assert 'function_buffer' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 1

    def test_incomplete_json_item(self, mock_styled_text):
        # Given incomplete JSON
        wrapper, args = self._create_wrapped_function([
            '{"foo": "bar",',
            ' "boolean"',
            ': true}'])

        # When
        response = wrapper(*args)

        # Then should tell the LLM the JSON response is incomplete and to continue
        # 'Expecting property name enclosed in double quotes: line 1 column 15 (char 14)'
        # "Expecting ':' delimiter: line 1 column 25 (char 24)"
        assert response == '{"foo": "bar", "boolean": true}'
        assert 'function_error' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 0

    def test_incomplete_json_array(self, mock_styled_text):
        # Given incomplete JSON
        wrapper, args = self._create_wrapped_function([
            '{"foo": "bar", "items": [1, 2, 3, "4"',
            ', 5]}'])

        # When
        response = wrapper(*args)

        # Then should tell the LLM the JSON response is incomplete and to continue
        # "Expecting ',' delimiter: line 1 column 24 (char 23)"
        assert response == '{"foo": "bar", "items": [1, 2, 3, "4", 5]}'
        assert 'function_error' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 0

    def test_incomplete_then_invalid_by_schema(self, mock_styled_text):
        # Given incomplete JSON
        wrapper, args = self._create_wrapped_function([
            '{"items": [1, 2, 3, "4"',
            ', 5]}',
            # Please try again with a valid JSON object, referring to the previous JSON schema I provided above
            '{"foo": "bar",',
            ' "items": [1, 2, 3, "4"',
            ', 5]}'
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM the JSON response is incomplete and to continue
        # "Expecting ',' delimiter: line 1 column 24 (char 23)"
        # "'foo' is a required property"
        assert response == '{"foo": "bar", "items": [1, 2, 3, "4", 5]}'
        assert 'function_error' not in args[0]
        # And the user should not need to be notified
        assert mock_styled_text.call_count == 0

    def test_invalid_boolean_max_retries(self, mock_styled_text):
        # Given invalid JSON boolean
        wrapper, args = self._create_wrapped_function([
            '{"boolean": True, "foo": "bar"}',
            '{"boolean": True,\n "foo": "bar"}',
            '{"boolean": True}',
            '{"boolean": true, "foo": "bar"}',
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM there is an error in the JSON response
        assert response == '{"boolean": true, "foo": "bar"}'
        assert args[0]['function_error'] == 'Invalid value: `True`'
        assert mock_styled_text.call_count == 1

    def test_extra_data(self, mock_styled_text):
        # Given invalid JSON boolean
        wrapper, args = self._create_wrapped_function([
            '{"boolean": true, "foo": "bar"}\n I hope that helps',
            '{"boolean": true, "foo": "bar"}\n I hope that helps',
            '{"boolean": true, "foo": "bar"}\n I hope that helps',
            '{"boolean": true, "foo": "bar"}',
        ])

        # When
        response = wrapper(*args)

        # Then should tell the LLM there is an error in the JSON response
        assert response == '{"boolean": true, "foo": "bar"}'
        # assert len(args[0]['function_error']) > 0
        assert args[0]['function_error'] == 'Extra data: line 2 column 2 (char 33)'
        assert mock_styled_text.call_count == 1


class TestSchemaValidation:
    def setup_method(self):
        self.function: FunctionType = {
            'name': 'test',
            'description': 'test schema',
            'parameters': {
                'type': 'object',
                'properties': {'foo': {'type': 'string'}},
                'required': ['foo']
            }
        }

    def test_assert_json_response(self):
        assert assert_json_response('{"foo": "bar"}')
        assert assert_json_response('{\n"foo": "bar"}')
        assert assert_json_response('```\n{"foo": "bar"}')
        assert assert_json_response('```json\n{\n"foo": "bar"}')
        with pytest.raises(ValueError, match='LLM did not respond with JSON'):
            assert assert_json_response('# Foo\n bar')

    def test_assert_json_schema(self):
        # When assert_json_schema is called with valid JSON
        # Then no errors
        assert (assert_json_schema('{"foo": "bar"}', [self.function]))

    def test_assert_json_schema_incomplete(self):
        # When assert_json_schema is called with incomplete JSON
        # Then error is raised
        with pytest.raises(JSONDecodeError):
            assert_json_schema('{"foo": "b', [self.function])

    def test_assert_json_schema_invalid(self):
        # When assert_json_schema is called with invalid JSON
        # Then error is raised
        with pytest.raises(ValidationError, match="1 is not of type 'string'"):
            assert_json_schema('{"foo": 1}', [self.function])

    def test_assert_json_schema_required(self):
        # When assert_json_schema is called with missing required property
        # Then error is raised
        self.function['parameters']['properties']['other'] = {'type': 'string'}
        self.function['parameters']['required'] = ['foo', 'other']

        with pytest.raises(ValidationError, match="'other' is a required property"):
            assert_json_schema('{"foo": "bar"}', [self.function])

    def test_DEVELOPMENT_PLAN(self):
        assert (assert_json_schema('''
{
  "plan": [
    {
      "description": "Set up project structure including creation of necessary directories and files. Initialize Node.js and install necessary libraries such as express and socket.io.",
      "user_review_goal": "Developer should be able to start an empty express server by running `npm start` command without any errors."
    },
    {
      "description": "Create a simple front-end HTML page with CSS and JavaScript that includes input for typing messages and area for displaying messages.",
      "user_review_goal": "Navigating to the root URL (http://localhost:3000) should display the chat front-end with an input box and a message area."
    },
    {
      "description": "Set up socket.io on the back-end to handle websocket connections and broadcasting messages to the clients.",
      "user_review_goal": "By using two different browsers or browser tabs, when one user sends a message from one tab, it should appear in the other user's browser tab in real-time."
    },
    {
      "description": "Integrate front-end with socket.io client to send messages from the input field to the server and display incoming messages in the message area.",
      "user_review_goal": "Typing a message in the chat input and sending it should then display the message in the chat area."
    }
  ]
}
'''.strip(), DEVELOPMENT_PLAN['definitions']))


class TestLlmConnection:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

    @patch('utils.llm_connection.requests.post')
    @patch('utils.llm_connection.time.sleep')
    def test_rate_limit_error(self, mock_sleep, mock_post, monkeypatch):
        project = Project({'app_id': 'test-app'})

        monkeypatch.setenv('OPENAI_API_KEY', 'secret')

        error_texts = [
            "Please try again in 6ms.",
            "Please try again in 1.2s.",
            "Please try again in 2m5.5s.",
        ]

        mock_responses = [Mock(status_code=429, text='''{
            "error": {
                "message": "Rate limit reached for 10KTPM-200RPM in organization org-OASFC7k1Ff5IzueeLArhQtnT on tokens per min. Limit: 10000 / min. ''' + error_text + '''",
                "type": "tokens",
                "param": null,
                "code": "rate_limit_exceeded"
            }
        }''') for error_text in error_texts]

        content = 'DONE'
        success_text = '{"id": "gen-123", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "' + content + '"}}]}'

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.iter_lines.return_value = [success_text.encode('utf-8')]

        # add the success at the end of the error requests
        mock_responses.append(mock_success_response)

        mock_post.side_effect = mock_responses

        wrapper = retry_on_exception(stream_gpt_completion)
        data = {
            'model': 'gpt-4',
            'messages': [{'role': 'user', 'content': 'testing'}]
        }

        # When
        response = wrapper(data, 'test', project)

        # Then
        assert response == {'text': 'DONE'}
        assert mock_sleep.call_args_list == [call(6.006), call(7.2), call(131.5)]

    @patch('utils.llm_connection.requests.post')
    def test_stream_gpt_completion(self, mock_post, monkeypatch):
        project = Project({'app_id': 'test-app'})

        # Given streaming JSON response
        monkeypatch.setenv('OPENAI_API_KEY', 'secret')
        deltas = ['{', '\\n',
                  '  \\"foo\\": \\"bar\\",', '\\n',
                  '  \\"prompt\\": \\"Hello\\",', '\\n',
                  '  \\"choices\\": []', '\\n',
                  '}']
        lines_to_yield = [
            ('{"id": "gen-123", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "' + delta + '"}}]}')
            .encode('utf-8')
            for delta in deltas
        ]
        lines_to_yield.insert(1, b': OPENROUTER PROCESSING')  # Simulate OpenRoute keep-alive pings
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = lines_to_yield

        mock_post.return_value = mock_response

        with patch('utils.llm_connection.requests.post', return_value=mock_response):
            # When
            response = stream_gpt_completion({
                'model': 'gpt-4',
                'messages': [],
            }, '', project)

            # Then
            assert response == {'text': '{\n  "foo": "bar",\n  "prompt": "Hello",\n  "choices": []\n}'}

    @pytest.mark.uses_tokens
    @pytest.mark.parametrize('endpoint, model', [
        ('OPENAI', 'gpt-4'),  # role: system
        ('OPENROUTER', 'openai/gpt-3.5-turbo'),  # role: user
        ('OPENROUTER', 'meta-llama/codellama-34b-instruct'),  # rule: user, is_llama
        ('OPENROUTER', 'google/palm-2-chat-bison'),  # role: user/system
        ('OPENROUTER', 'google/palm-2-codechat-bison'),
        ('OPENROUTER', 'anthropic/claude-2'),  # role: user, is_llama
    ])
    def test_chat_completion_Architect(self, endpoint, model, monkeypatch):
        # Given
        monkeypatch.setenv('ENDPOINT', endpoint)
        monkeypatch.setenv('MODEL_NAME', model)
        project = Project({'app_id': 'test-app'})

        agent = Architect(project)
        convo = AgentConvo(agent)
        convo.construct_and_add_message_from_prompt('architecture/technologies.prompt',
                                                    {
                                                        'name': 'Test App',
                                                        'app_summary': '''
The project involves the development of a web-based chat application named "Test_App".
In this application, users can send direct messages to each other.
However, it does not include a group chat functionality.
Multimedia messaging, such as the exchange of images and videos, is not a requirement for this application.
No clear instructions were given for the inclusion of user profile customization features like profile
picture and status updates, as well as a feature for chat history. The project must be developed strictly
as a monolithic application, regardless of any other suggested methods.
The project's specifications are subject to the project manager's discretion, implying a need for
solution-oriented decision-making in areas where precise instructions were not provided.''',
                                                        'app_type': 'web app',
                                                        'user_stories': [
                                                            'User will be able to send direct messages to another user.',
                                                            'User will receive direct messages from other users.',
                                                            'User will view the sent and received messages in a conversation view.',
                                                            'User will select a user to send a direct message.',
                                                            'User will be able to search for users to send direct messages to.',
                                                            'Users can view the online status of other users.',
                                                            'User will be able to log into the application using their credentials.',
                                                            'User will be able to logout from the Test_App.',
                                                            'User will be able to register a new account on Test_App.',
                                                        ]
                                                    })
        function_calls = ARCHITECTURE

        # When
        response = create_gpt_chat_completion(convo.messages, '', project, function_calls=function_calls)

        # Then
        assert convo.messages[0]['content'].startswith('You are an experienced software architect')
        assert convo.messages[1]['content'].startswith('You are working in a software development agency')

        assert response is not None
        response = parse_agent_response(response, function_calls)
        assert 'Node.js' in response['technologies']

    @pytest.mark.uses_tokens
    @pytest.mark.parametrize('endpoint, model', [
        ('OPENAI', 'gpt-4'),
        ('OPENROUTER', 'openai/gpt-3.5-turbo'),
        ('OPENROUTER', 'meta-llama/codellama-34b-instruct'),
        ('OPENROUTER', 'phind/phind-codellama-34b-v2'),
        ('OPENROUTER', 'google/palm-2-chat-bison'),
        ('OPENROUTER', 'google/palm-2-codechat-bison'),
        ('OPENROUTER', 'anthropic/claude-2'),
        ('OPENROUTER', 'mistralai/mistral-7b-instruct')
    ])
    def test_chat_completion_TechLead(self, endpoint, model, monkeypatch):
        # Given
        monkeypatch.setenv('ENDPOINT', endpoint)
        monkeypatch.setenv('MODEL_NAME', model)
        project = Project({'app_id': 'test-app'})

        agent = TechLead(project)
        convo = AgentConvo(agent)
        convo.construct_and_add_message_from_prompt('development/plan.prompt',
                                                    {
                                                        'name': 'Test App',
                                                        'app_summary': '''
    The project entails creating a web-based chat application, tentatively named "chat_app."
This application does not require user authentication or chat history storage.
It solely supports one-on-one messaging, excluding group chats or multimedia sharing like photos, videos, or files.
Additionally, there are no specific requirements for real-time functionality, like live typing indicators or read receipts.
The development of this application will strictly follow a monolithic structure, avoiding the use of microservices, as per the client's demand.
The development process will include the creation of user stories and tasks, based on detailed discussions with the client.''',
                                                        'app_type': 'web app',
                                                        'user_stories': [
                                                            'User Story 1: As a user, I can access the web-based "chat_app" directly without needing to authenticate or log in. Do you want to add anything else? If not, just press ENTER.',
                                                            'User Story 2: As a user, I can start one-on-one conversations with another user on the "chat_app". Do you want to add anything else? If not, just press ENTER.',
                                                            'User Story 3: As a user, I can send and receive messages in real-time within my one-on-one conversation on the "chat_app". Do you want to add anything else? If not, just press ENTER.',
                                                            'User Story 4: As a user, I do not need to worry about deleting or storing my chats because the "chat_app" does not store chat histories. Do you want to add anything else? If not, just press ENTER.',
                                                            'User Story 5: As a user, I will only be able to send text messages, as the "chat_app" does not support any kind of multimedia sharing like photos, videos, or files. Do you want to add anything else? If not, just press ENTER.',
                                                            'User Story 6: As a user, I will not see any live typing indicators or read receipts since the "chat_app" does not provide any additional real-time functionality beyond message exchange. Do you want to add anything else? If not, just press ENTER.',
                                                        ]
                                                    })
        function_calls = DEVELOPMENT_PLAN

        # Retry on bad LLM responses
        # mock_questionary = MockQuestionary(['', '', 'no'])

        # with patch('utils.llm_connection.questionary', mock_questionary):
        # When
        response = create_gpt_chat_completion(convo.messages, '', project, function_calls=function_calls)

        # Then
        assert convo.messages[0]['content'].startswith('You are a tech lead in a software development agency')
        assert convo.messages[1]['content'].startswith(
            'You are working in a software development agency and a project manager and software architect approach you')

        assert response is not None
        response = parse_agent_response(response, function_calls)
        assert_non_empty_string(response['plan'][0]['description'])
        assert_non_empty_string(response['plan'][0]['user_review_goal'])
