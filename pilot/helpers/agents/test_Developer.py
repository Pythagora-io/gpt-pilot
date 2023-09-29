import builtins
import os
import pytest
from unittest.mock import patch

from helpers.AgentConvo import AgentConvo
from dotenv import load_dotenv
load_dotenv()

from main import get_custom_print
from .Developer import Developer, ENVIRONMENT_SETUP_STEP
from helpers.Project import Project
from test.mock_questionary import MockQuestionary


class TestDeveloper:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

        name = 'TestDeveloper'
        self.project = Project({
                'app_id': 'test-developer',
                'name': name,
                'app_type': ''
            },
            name=name,
            architecture=[],
            user_stories=[]
        )

        self.project.root_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/TestDeveloper'))
        self.project.technologies = []
        self.project.current_step = ENVIRONMENT_SETUP_STEP
        self.developer = Developer(self.project)

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"command": "python --version", "timeout": 10}'})
    @patch('helpers.cli.styled_text', return_value='no')
    @patch('helpers.cli.execute_command', return_value=('', 'DONE'))
    def test_install_technology(self, mock_execute_command, mock_styled_text,
                                mock_completion, mock_save, mock_get_saved_step):
        # Given
        self.developer.convo_os_specific_tech = AgentConvo(self.developer)

        # When
        llm_response = self.developer.install_technology('python')

        # Then
        assert llm_response == 'DONE'
        mock_execute_command.assert_called_once_with(self.project, 'python --version', 10)

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    # GET_TEST_TYPE has optional properties, so we need to be able to handle missing args.
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"type": "command_test", "command": {"command": "npm run test", "timeout": 3000}}'})
    # 2nd arg of return_value: `None` to debug, 'DONE' if successful
    @patch('helpers.cli.execute_command', return_value=('stdout:\n```\n\n```', 'DONE'))
    # @patch('helpers.cli.ask_user', return_value='yes')
    # @patch('helpers.cli.get_saved_command_run')
    def test_code_changes_command_test(self, mock_get_saved_step, mock_save, mock_chat_completion,
                               # Note: the 2nd line below will use the LLM to debug, uncomment the @patches accordingly
                               mock_execute_command):
                               # mock_ask_user, mock_get_saved_command_run):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name

        # When
        # "Now, we need to verify if this change was successfully implemented...
        result = self.developer.test_code_changes(monkey, convo)

        # Then
        assert result == {'success': True, 'cli_response': 'stdout:\n```\n\n```'}

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    # GET_TEST_TYPE has optional properties, so we need to be able to handle missing args.
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"type": "manual_test", "manual_test_description": "Does it look good?"}'})
    @patch('helpers.Project.ask_user', return_value='continue')
    def test_code_changes_manual_test_continue(self, mock_get_saved_step, mock_save, mock_chat_completion, mock_ask_user):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name

        # When
        result = self.developer.test_code_changes(monkey, convo)

        # Then
        assert result == {'success': True, 'user_input': 'continue'}

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('helpers.AgentConvo.create_gpt_chat_completion')
    @patch('utils.questionary.get_saved_user_input')
    # https://github.com/Pythagora-io/gpt-pilot/issues/35
    def test_code_changes_manual_test_no(self, mock_get_saved_user_input, mock_chat_completion, mock_save, mock_get_saved_step):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name
        convo.load_branch = lambda function_uuid=None: function_uuid
        self.project.developer = self.developer

        mock_chat_completion.side_effect = [
            {'text': '{"type": "manual_test", "manual_test_description": "Does it look good?"}'},
            {'text': '{"steps": [{"type": "command", "command": {"command": "something scary", "timeout": 3000}, "check_if_fixed": true}]}'},
            {'text': 'do something else scary'},
        ]

        mock_questionary = MockQuestionary(['no', 'no'])

        with patch('utils.questionary.questionary', mock_questionary):
            # When
            result = self.developer.test_code_changes(monkey, convo)

            # Then
            assert result == {'success': True, 'user_input': 'continue'}
