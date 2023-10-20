import builtins

import pytest
import os
from dotenv import load_dotenv
from unittest.mock import patch
from database.models.files import File
from main import get_custom_print
from helpers.test_Project import create_project
from .TechnicalWriter import TechnicalWriter

load_dotenv()


class TestProductOwner:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch.object(File, 'insert')
    def test_document_project(self, mock_insert, mock_get_step):
        # Given
        project = create_project()
        product_owner = TechnicalWriter(project)
        project.project_description = '''
The application to be developed, named "chat_app", is a web-based one-to-one chat application. 
It does not support image, file sharing and does not feature any type of data persistence, such as storing chat history. 
No user registration or authentication mechanism will be implemented and the application will not support real-time chat. 
This is to be monolithic application without use, creation or suggestion of any microservices.
        '''
        project.architecture = ["Node.js", "MongoDB", "Mongoose", "Bootstrap", "Vanilla JavaScript", "Socket.io", "Cronjob"]

        # When
        product_owner.document_project()

        # Then
        with open(os.path.join(project.root_path, 'README.md'), 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
            assert file_content != ''
