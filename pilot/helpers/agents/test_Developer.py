import builtins
import os
from unittest.mock import patch, Mock

from helpers.AgentConvo import AgentConvo
from dotenv import load_dotenv
load_dotenv()

from main import  get_custom_print
from .Developer import Developer, ENVIRONMENT_SETUP_STEP
from helpers.Project import Project
from test.mock_terminal_size import mock_terminal_size


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

    # @pytest.mark.uses_tokens
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
