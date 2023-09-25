import builtins
import pytest
from dotenv import load_dotenv

from const.function_calls import ARCHITECTURE, DEV_STEPS
from helpers.AgentConvo import AgentConvo
from helpers.Project import Project
from helpers.agents.Architect import Architect
from helpers.agents.Developer import Developer
from utils.function_calling import parse_agent_response
from .llm_connection import create_gpt_chat_completion
from main import get_custom_print

load_dotenv()

project = Project({'app_id': 'test-app'}, current_step='test')


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
