import re
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
load_dotenv()

from .CodeMonkey import CodeMonkey
from .Developer import Developer
from database.models.files import File
from database.models.development_steps import DevelopmentSteps
from helpers.Project import Project, update_file, clear_directory
from helpers.AgentConvo import AgentConvo
from test.test_utils import mock_terminal_size

SEND_TO_LLM = False
WRITE_TO_FILE = False


class TestCodeMonkey:
    def setup_method(self):
        name = 'TestDeveloper'
        self.project = Project({
                'app_id': 'test-developer',
                'name': name,
                'app_type': ''
            },
            name=name,
            architecture=[],
            user_stories=[],
            current_step='coding',
        )

        self.project.set_root_path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/TestDeveloper')))
        self.project.technologies = []
        last_step = DevelopmentSteps()
        last_step.id = 1
        self.project.checkpoints = {'last_development_step': last_step}
        self.project.app = None
        self.developer = Developer(self.project)
        self.codeMonkey = CodeMonkey(self.project, developer=self.developer)

    @patch('helpers.AgentConvo.get_saved_development_step', return_value=None)
    @patch('helpers.AgentConvo.save_development_step')
    @patch('os.get_terminal_size', mock_terminal_size)
    @patch.object(File, 'insert')
    def test_implement_code_changes(self, mock_get_dev, mock_save_dev, mock_file_insert):
        # Given
        code_changes_description = "Write the word 'Washington' to a .txt file"

        if SEND_TO_LLM:
            convo = AgentConvo(self.codeMonkey)
        else:
            convo = MagicMock()
            mock_responses = [
                # [],
                [{
                    'content': 'Washington',
                    'description': "A new .txt file with the word 'Washington' in it.",
                    'name': 'washington.txt',
                    'path': 'washington.txt'
                }]
            ]
            convo.send_message.side_effect = mock_responses

        if WRITE_TO_FILE:
            self.codeMonkey.implement_code_changes(convo, code_changes_description)
        else:
            # don't write the file, just
            with patch.object(Project, 'save_file') as mock_save_file:
                # When
                self.codeMonkey.implement_code_changes(convo, code_changes_description)

                # Then
                mock_save_file.assert_called_once()
                called_data = mock_save_file.call_args[0][0]
                assert re.match(r'\w+\.txt$', called_data['name'])
                assert (called_data['path'] == '/' or called_data['path'] == called_data['name'])
                assert called_data['content'] == 'Washington'

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('os.get_terminal_size', mock_terminal_size)
    @patch.object(File, 'insert')
    def test_implement_code_changes_with_read(self, mock_get_dev, mock_save_dev, mock_file_insert):
        # Given
        code_changes_description = "Read the file called file_to_read.txt and write its content to a file called output.txt"
        workspace = self.project.root_path
        update_file(os.path.join(workspace, 'file_to_read.txt'), 'Hello World!\n')

        if SEND_TO_LLM:
            convo = AgentConvo(self.codeMonkey)
        else:
            convo = MagicMock()
            mock_responses = [
                # ['file_to_read.txt', 'output.txt'],
                [{
                    'content': 'Hello World!\n',
                    'description': 'This file is the output file. The content of file_to_read.txt is copied into this file.',
                    'name': 'output.txt',
                    'path': 'output.txt'
                }]
            ]
            convo.send_message.side_effect = mock_responses

        if WRITE_TO_FILE:
            self.codeMonkey.implement_code_changes(convo, code_changes_description)
        else:
            with patch.object(Project, 'save_file') as mock_save_file:
                # When
                self.codeMonkey.implement_code_changes(convo, code_changes_description)

                # Then
                clear_directory(workspace)
                mock_save_file.assert_called_once()
                called_data = mock_save_file.call_args[0][0]
                assert called_data['name'] == 'output.txt'
                assert (called_data['path'] == '/' or called_data['path'] == called_data['name'])
                assert called_data['content'] == 'Hello World!\n'
