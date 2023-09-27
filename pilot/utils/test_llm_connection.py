import builtins
from json import JSONDecodeError

import pytest
from unittest.mock import patch, Mock
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
from utils.llm_connection import create_gpt_chat_completion, stream_gpt_completion, assert_json_response, assert_json_schema
from main import get_custom_print

load_dotenv()

project = Project({'app_id': 'test-app'}, current_step='test')


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
        assert(assert_json_schema('{"foo": "bar"}', [self.function]))

    def test_assert_json_schema_invalid(self):
        # When assert_json_schema is called with invalid JSON
        # Then error is raised
        with pytest.raises(ValidationError, match="1 is not of type 'string'"):
            assert_json_schema('{"foo": 1}', [self.function])

    def test_assert_json_schema_incomplete(self):
        # When assert_json_schema is called with incomplete JSON
        # Then error is raised
        with pytest.raises(JSONDecodeError):
            assert_json_schema('{"foo": "b', [self.function])

    def test_assert_json_schema_required(self):
        # When assert_json_schema is called with missing required property
        # Then error is raised
        self.function['parameters']['properties']['other'] = {'type': 'string'}
        self.function['parameters']['required'] = ['foo', 'other']

        with pytest.raises(ValidationError, match="'other' is a required property"):
            assert_json_schema('{"foo": "bar"}', [self.function])

    def test_DEVELOPMENT_PLAN(self):
        assert(assert_json_schema('''
{
  "plan": [
    {
      "description": "Set up project structure including creation of necessary directories and files. Initialize Node.js and install necessary libraries such as express and socket.io.",
      "programmatic_goal": "Project structure should be set up and Node.js initialized. Express and socket.io libraries should be installed and reflected in the package.json file.",
      "user_review_goal": "Developer should be able to start an empty express server by running `npm start` command without any errors."
    },
    {
      "description": "Create a simple front-end HTML page with CSS and JavaScript that includes input for typing messages and area for displaying messages.",
      "programmatic_goal": "There should be an HTML file containing an input box for typing messages and an area for displaying the messages. This HTML page should be served when user navigates to the root URL.",
      "user_review_goal": "Navigating to the root URL (http://localhost:3000) should display the chat front-end with an input box and a message area."
    },
    {
      "description": "Set up socket.io on the back-end to handle websocket connections and broadcasting messages to the clients.",
      "programmatic_goal": "Server should be able to handle websocket connections using socket.io and broadcast messages to all connected clients.",
      "user_review_goal": "By using two different browsers or browser tabs, when one user sends a message from one tab, it should appear in the other user's browser tab in real-time."
    },
    {
      "description": "Integrate front-end with socket.io client to send messages from the input field to the server and display incoming messages in the message area.",
      "programmatic_goal": "Front-end should be able to send messages to server and display incoming messages in the message area using socket.io client.",
      "user_review_goal": "Typing a message in the chat input and sending it should then display the message in the chat area."
    }
  ]
}
'''.strip(), DEVELOPMENT_PLAN['definitions']))

class TestLlmConnection:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

    @patch('utils.llm_connection.requests.post')
    def test_stream_gpt_completion(self, mock_post, monkeypatch):
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

        # When
        with patch('utils.llm_connection.requests.post', return_value=mock_response):
            response = stream_gpt_completion({}, '')

            # Then
            assert response == {'text': '{\n  "foo": "bar",\n  "prompt": "Hello",\n  "choices": []\n}'}


    @pytest.mark.uses_tokens
    @pytest.mark.parametrize('endpoint, model', [
        ('OPENAI', 'gpt-4'),                                 # role: system
        ('OPENROUTER', 'openai/gpt-3.5-turbo'),              # role: user
        ('OPENROUTER', 'meta-llama/codellama-34b-instruct'), # rule: user, is_llama
        ('OPENROUTER', 'google/palm-2-chat-bison'),          # role: user/system
        ('OPENROUTER', 'google/palm-2-codechat-bison'),
        ('OPENROUTER', 'anthropic/claude-2'),              # role: user, is_llama
    ])
    def test_chat_completion_Architect(self, endpoint, model, monkeypatch):
        # Given
        monkeypatch.setenv('ENDPOINT', endpoint)
        monkeypatch.setenv('MODEL_NAME', model)

        agent = Architect(project)
        convo = AgentConvo(agent)
        convo.construct_and_add_message_from_prompt('architecture/technologies.prompt',
                                                        {
                                                            'name': 'Test App',
                                                            'prompt': '''
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
        response = create_gpt_chat_completion(convo.messages, '', function_calls=function_calls)

        # Then
        assert convo.messages[0]['content'].startswith('You are an experienced software architect')
        assert convo.messages[1]['content'].startswith('You are working in a software development agency')

        assert response is not None
        response = parse_agent_response(response, function_calls)
        assert 'Node.js' in response

    @pytest.mark.uses_tokens
    @pytest.mark.parametrize('endpoint, model', [
        ('OPENAI', 'gpt-4'),
        ('OPENROUTER', 'openai/gpt-3.5-turbo'),
        ('OPENROUTER', 'meta-llama/codellama-34b-instruct'),
        ('OPENROUTER', 'google/palm-2-chat-bison'),
        ('OPENROUTER', 'google/palm-2-codechat-bison'),
        ('OPENROUTER', 'anthropic/claude-2'),
    ])
    def test_chat_completion_TechLead(self, endpoint, model, monkeypatch):
        # Given
        monkeypatch.setenv('ENDPOINT', endpoint)
        monkeypatch.setenv('MODEL_NAME', model)

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
        mock_questionary = MockQuestionary(['', '', 'no'])

        # When
        with patch('utils.llm_connection.questionary', mock_questionary):
            response = create_gpt_chat_completion(convo.messages, '', function_calls=function_calls)

            # Then
            assert convo.messages[0]['content'].startswith('You are a tech lead in a software development agency')
            assert convo.messages[1]['content'].startswith('You are working in a software development agency and a project manager and software architect approach you')

            assert response is not None
            response = parse_agent_response(response, function_calls)
            assert_non_empty_string(response[0]['description'])
            assert_non_empty_string(response[0]['programmatic_goal'])
            assert_non_empty_string(response[0]['user_review_goal'])


    # def test_break_down_development_task(self):
    #     # Given
    #     agent = Developer(project)
    #     convo = AgentConvo(agent)
    #     # convo.construct_and_add_message_from_prompt('architecture/technologies.prompt',
    #     #                                             {
    #     #                                                 'name': 'Test App',
    #     #                                                 'prompt': '''
    #
    #     function_calls = DEV_STEPS
    #
    #     # When
    #     response = create_gpt_chat_completion(convo.messages, '', function_calls=function_calls)
    #     # response = {'function_calls': {
    #     #     'name': 'break_down_development_task',
    #     #     'arguments': {'tasks': [{'type': 'command', 'description': 'Run the app'}]}
    #     # }}
    #     response = parse_agent_response(response, function_calls)
    #
    #     # Then
    #     # assert len(convo.messages) == 2
    #     assert response == ([{'type': 'command', 'description': 'Run the app'}], 'more_tasks')

    def _create_convo(self, agent):
        convo = AgentConvo(agent)
