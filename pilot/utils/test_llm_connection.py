import builtins
from dotenv import load_dotenv
from const.function_calls import ARCHITECTURE
from helpers.AgentConvo import AgentConvo
from helpers.Project import Project
from helpers.agents.Architect import Architect
from .llm_connection import create_gpt_chat_completion
from main import get_custom_print

load_dotenv()

project = Project({'app_id': 'test-app'}, current_step='test')


class TestLlmConnection:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

    def test_chat_completion_Architect(self):
        """Test the chat completion method."""
        # Given
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

        messages = convo.messages
        # messages = [{"role": "user", "content": "I want to create a website"}]

        # When
        response = create_gpt_chat_completion(messages, '', function_calls=ARCHITECTURE)
        # Then
        # You are and experienced software architect...
        # You are working in a software development agency...
        assert len(convo.messages) == 2
        assert response is not None
        assert len(response) > 0
        technologies: list[str] = response['function_calls']['arguments']['technologies']
        assert 'Node.js' in technologies


    def _create_convo(self, agent):
        convo = AgentConvo(agent)