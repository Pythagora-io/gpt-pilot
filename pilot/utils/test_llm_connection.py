import builtins
import pytest
from dotenv import load_dotenv

from const.function_calls import ARCHITECTURE, DEVELOPMENT_PLAN
from helpers.AgentConvo import AgentConvo
from helpers.Project import Project
from helpers.agents.Architect import Architect
from helpers.agents.TechLead import TechLead
from utils.function_calling import parse_agent_response, FunctionType
from test.test_utils import assert_non_empty_string
from .llm_connection import create_gpt_chat_completion, assert_json_response, assert_json_schema
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
        with pytest.raises(ValueError, match='LLM responded with invalid JSON'):
            assert_json_schema('{"foo": 1}', [self.function])

    def test_assert_json_schema_incomplete(self):
        # When assert_json_schema is called with incomplete JSON
        # Then error is raised
        with pytest.raises(ValueError, match='LLM responded with invalid JSON'):
            assert_json_schema('{"foo": "b', [self.function])

    def test_assert_json_schema_required(self):
        # When assert_json_schema is called with missing required property
        # Then error is raised
        self.function['parameters']['properties']['other'] = {'type': 'string'}
        self.function['parameters']['required'] = ['foo', 'other']

        with pytest.raises(ValueError, match='LLM responded with invalid JSON'):
            assert_json_schema('{"foo": "bar"}', [self.function])

class TestLlmConnection:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})



    @pytest.mark.uses_tokens
    @pytest.mark.parametrize("endpoint, model", [
        ("OPENAI", "gpt-4"),                                 # role: system
        ("OPENROUTER", "openai/gpt-3.5-turbo"),              # role: user
        ("OPENROUTER", "meta-llama/codellama-34b-instruct"), # rule: user, is_llama
        ("OPENROUTER", "google/palm-2-chat-bison"),          # role: user/system
        ("OPENROUTER", "google/palm-2-codechat-bison"),
        # TODO: See https://github.com/1rgs/jsonformer-claude/blob/main/jsonformer_claude/main.py
        #           https://github.com/guidance-ai/guidance - token healing
        ("OPENROUTER", "anthropic/claude-2"),              # role: user, is_llama
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
    @pytest.mark.parametrize("endpoint, model", [
        ("OPENAI", "gpt-4"),  # role: system
        ("OPENROUTER", "openai/gpt-3.5-turbo"),  # role: user
        ("OPENROUTER", "meta-llama/codellama-34b-instruct"),  # rule: user, is_llama
        ("OPENROUTER", "google/palm-2-chat-bison"),  # role: user/system
        ("OPENROUTER", "google/palm-2-codechat-bison"),
        # TODO: See https://github.com/1rgs/jsonformer-claude/blob/main/jsonformer_claude/main.py
        #           https://github.com/guidance-ai/guidance - token healing
        ("OPENROUTER", "anthropic/claude-2"),  # role: user, is_llama
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

        # When
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
