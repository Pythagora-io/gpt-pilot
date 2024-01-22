import builtins
import os
import pytest
from unittest.mock import patch
from dotenv import load_dotenv
load_dotenv()

from main import get_custom_print
from helpers.agents.TechLead import TechLead, DEVELOPMENT_PLANNING_STEP
from helpers.Project import Project
from test.test_utils import assert_non_empty_string
from test.mock_questionary import MockQuestionary


class TestTechLead:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

        name = 'TestTechLead'
        self.project = Project({
                'app_id': 'test-tech-lead',
                'name': name,
                'app_type': ''
            },
            name=name,
            architecture=[],
            user_stories=[]
        )

        self.project.set_root_path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/TestTechLead')))
        self.project.technologies = []
        self.project.project_description = '''
The project entails creating a web-based chat application, tentatively named "chat_app." 
This application does not require user authentication or chat history storage. 
It solely supports one-on-one messaging, excluding group chats or multimedia sharing like photos, videos, or files. 
Additionally, there are no specific requirements for real-time functionality, like live typing indicators or read receipts. 
The development of this application will strictly follow a monolithic structure, avoiding the use of microservices, as per the client's demand. 
The development process will include the creation of user stories and tasks, based on detailed discussions with the client. 
        '''
        self.project.user_stories = [
            'User Story 1: As a user, I can access the web-based "chat_app" directly without needing to authenticate or log in. Do you want to add anything else? If not, just press ENTER.',
            'User Story 2: As a user, I can start one-on-one conversations with another user on the "chat_app". Do you want to add anything else? If not, just press ENTER.',
            'User Story 3: As a user, I can send and receive messages in real-time within my one-on-one conversation on the "chat_app". Do you want to add anything else? If not, just press ENTER.',
            'User Story 4: As a user, I do not need to worry about deleting or storing my chats because the "chat_app" does not store chat histories. Do you want to add anything else? If not, just press ENTER.',
            'User Story 5: As a user, I will only be able to send text messages, as the "chat_app" does not support any kind of multimedia sharing like photos, videos, or files. Do you want to add anything else? If not, just press ENTER.',
            'User Story 6: As a user, I will not see any live typing indicators or read receipts since the "chat_app" does not provide any additional real-time functionality beyond message exchange. Do you want to add anything else? If not, just press ENTER.',
        ]
        self.project.architecture = ['Node.js', 'Socket.io', 'Bootstrap', 'JavaScript', 'HTML5', 'CSS3']
        self.project.current_step = DEVELOPMENT_PLANNING_STEP

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step', return_value=None)
    @patch('helpers.agents.TechLead.save_progress', return_value=None)
    @patch('helpers.agents.TechLead.get_progress_steps', return_value=None)
    def test_create_development_plan(self, mock_get_saved_step, mock_save_progress, mock_get_progress_steps):
        self.techLead = TechLead(self.project)

        mock_questionary = MockQuestionary(['', '', 'no'])

        with patch('utils.questionary.questionary', mock_questionary):
            # When
            development_plan = self.techLead.create_development_plan()

            # Then
            assert development_plan is not None
            assert_non_empty_string(development_plan[0]['description'])
            assert_non_empty_string(development_plan[0]['user_review_goal'])
