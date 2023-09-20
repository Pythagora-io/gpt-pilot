from dotenv import load_dotenv
from const.function_calls import ARCHITECTURE
from helpers.AgentConvo import AgentConvo
from helpers.Project import Project
from helpers.agents.Architect import Architect
from .llm_connection import create_gpt_chat_completion

load_dotenv()

project = Project({'app_id': 'test-app'}, current_step='test')


class TestLlmConnection:
    """Test the LLM connection class."""

    def test_chat_completion_Architect(self):
        """Test the chat completion method."""
        # Given
        agent = Architect(project)
        convo = AgentConvo(agent)
        convo.construct_and_add_message_from_prompt('architecture/technologies.prompt',
                                                    {
                                                        'name': 'Test App',
                                                        'prompt': 'A web-based chat app',
                                                        'app_type': 'web app',
                                                        'user_stories': [
                                                            'As a user I want to be able view messages sent and received'
                                                        ]
                                                    })

        messages = convo.messages
        # messages = [{"role": "user", "content": "I want to create a website"}]

        # When
        response = create_gpt_chat_completion(messages, '', function_calls=ARCHITECTURE)
        # Then
        assert response is not None
        assert len(response) > 0
        # assert response != prompt


    def _create_convo(self, agent):
        convo = AgentConvo(agent)