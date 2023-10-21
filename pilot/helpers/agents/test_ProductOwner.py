import builtins

import pytest
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
from main import get_custom_print
from helpers.test_Project import create_project
from .ProductOwner import ProductOwner

load_dotenv()


class TestProductOwner:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

    @patch('prompts.prompts.ask_user', return_value='yes')
    @patch('prompts.prompts.create_gpt_chat_completion')
    def test_ask_clarifying_questions(self, mock_completion, mock_ask):
        # Given
        project = create_project()
        product_owner = ProductOwner(project)
        mock_completion.side_effect = [
            {'text': 'Will the app run in the console?'},
            {'text': 'Will it always print "Hello World"?'},
            {'text': 'EVERYTHING_CLEAR'}
        ]

        # When
        high_level_messages = product_owner.ask_clarifying_questions('A Python version of the typical "hello world" application.')

        # Then
        for msg in high_level_messages:
            assert msg['role'] != 'system'
            assert 'You are an experienced project owner' not in msg['content']
            assert 'I\'m going to show you an overview of tasks' not in msg['content']
            assert 'Getting additional answers' not in msg['content']

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step')
    # @patch('helpers.AgentConvo.create_gpt_chat_completion', return_value={'text': 'A python app which displays "Hello World" on the console'})
    def test_generate_project_summary(self,
                                      # mock_completion,
                                      mock_get_step):
        # Given
        project = create_project()
        product_owner = ProductOwner(project)

        # When
        summary = product_owner.generate_project_summary([
            {'role': 'user', 'content': 'I want you to create the app (let\'s call it "TestProject") that can be described like this:\n'
                                        '```\nA Python version of the typical "hello world" application.\n```'},
            {'role': 'assistant', 'content': 'Should the application produce a text-based output?'},
            {'role': 'user', 'content': 'yes'},
            {'role': 'assistant', 'content': 'Should the application be command-line based or should it have a GUI (Graphical User Interface)?'},
            {'role': 'user', 'content': 'command-line'},
            {'role': 'assistant', 'content': 'Is there a specific version of Python you prefer the application to be written in?'},
            {'role': 'user', 'content': 'no'},
            {'role': 'assistant', 'content': 'Are there any specific packages or libraries you want to be used in the development of this application?'},
            {'role': 'user', 'content': 'no'},
        ])

        # Then the summary should not include instructions as reported in #246
        assert isinstance(summary, str)
        assert 'EVERYTHING_CLEAR' not in summary
        assert 'neutral tone' not in summary
        assert 'clarification' not in summary
