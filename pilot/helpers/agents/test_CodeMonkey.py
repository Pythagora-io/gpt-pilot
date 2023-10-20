import builtins
import json
import re
import os
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
load_dotenv()

from main import get_custom_print
from .CodeMonkey import CodeMonkey
from .Developer import Developer
from database.models.files import File
from database.models.development_steps import DevelopmentSteps
from helpers.Project import Project, update_file, clear_directory
from helpers.AgentConvo import AgentConvo
from test.test_utils import mock_terminal_size
from helpers.test_Project import create_project

SEND_TO_LLM = False
WRITE_TO_FILE = False


class TestCodeMonkey:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

        name = 'TestDeveloper'
        self.project = create_project('TestCodeMonkey')
        self.project.technologies = []
        last_step = DevelopmentSteps()
        last_step.id = 1
        self.project.checkpoints = {'last_development_step': last_step}
        self.developer = Developer(self.project)
        self.code_monkey = CodeMonkey(self.project, developer=self.developer)

    @patch('helpers.AgentConvo.get_saved_development_step', return_value=None)
    @patch('helpers.AgentConvo.save_development_step')
    @patch('os.get_terminal_size', mock_terminal_size)
    @patch.object(File, 'insert')
    def test_implement_code_changes(self, mock_get_dev, mock_save_dev, mock_file_insert):
        # Given
        code_changes_description = "Write the word 'Washington' to a .txt file"

        if SEND_TO_LLM:
            convo = AgentConvo(self.code_monkey)
        else:
            convo = MagicMock()
            mock_responses = [
                # [],
                {'files': [{
                    'content': 'Washington',
                    'description': "A new .txt file with the word 'Washington' in it.",
                    'name': 'washington.txt',
                    'path': 'washington.txt'
                }]}
            ]
            convo.send_message.side_effect = mock_responses

        if WRITE_TO_FILE:
            self.code_monkey.implement_code_changes(convo, code_changes_description)
        else:
            # don't write the file, just
            with patch.object(Project, 'save_file') as mock_save_file:
                # When
                self.code_monkey.implement_code_changes(convo, code_changes_description)

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
            convo = AgentConvo(self.code_monkey)
        else:
            convo = MagicMock()
            mock_responses = [
                # ['file_to_read.txt', 'output.txt'],
                {'files': [{
                    'content': 'Hello World!\n',
                    'description': 'This file is the output file. The content of file_to_read.txt is copied into this file.',
                    'name': 'output.txt',
                    'path': 'output.txt'
                }]}
            ]
            convo.send_message.side_effect = mock_responses

        if WRITE_TO_FILE:
            self.code_monkey.implement_code_changes(convo, code_changes_description)
        else:
            with patch.object(Project, 'save_file') as mock_save_file:
                # When
                self.code_monkey.implement_code_changes(convo, code_changes_description)

                # Then
                clear_directory(workspace)
                mock_save_file.assert_called_once()
                called_data = mock_save_file.call_args[0][0]
                assert called_data['name'] == 'output.txt'
                assert (called_data['path'] == '/' or called_data['path'] == called_data['name'])
                assert called_data['content'] == 'Hello World!\n'

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step', return_value=None)
    @patch('helpers.agents.TechLead.save_progress', return_value=None)
    @patch('helpers.agents.TechLead.get_progress_steps', return_value=None)
    @patch.object(File, 'insert')
    def test_create_project_scripts_python(self, mock_insert, mock_get_saved_step, mock_save_progress, mock_get_progress_steps):
        # Given
        self.project.architecture = ['Python', 'FastAPI']

        # When
        self.code_monkey.create_project_scripts()

        # Then
        pass

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step', return_value=None)
    @patch('helpers.agents.TechLead.save_progress', return_value=None)
    @patch('helpers.agents.TechLead.get_progress_steps', return_value=None)
    @patch.object(File, 'insert')
    def test_create_project_scripts_node(self, mock_insert, mock_get_saved_step, mock_save_progress,
                                    mock_get_progress_steps):
        # Given
        self.project.architecture = ['Node.js', 'Socket.io', 'Bootstrap', 'JavaScript', 'HTML5', 'CSS3']
        self.project.save_file({'path': 'package.json', 'content': json.dumps({'name': 'test'})})

        # When
        self.code_monkey.create_project_scripts()

        # Then
        pass