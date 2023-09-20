import builtins
import pytest
from unittest.mock import patch
from dotenv import load_dotenv
load_dotenv()

from database.database import create_tables
from helpers.Project import Project
from .main import init, get_custom_print


def test_init():
    # When
    args = init()

    # Then
    for field in ['app_id', 'user_id', 'email']:
        assert args[field] is not None

    for field in ['workspace', 'step']:
        assert args[field] is None


class MockQuestionary():
    def __init__(self, answers=[]):
        self.answers = iter(answers)
        self.state = 'project_description'

    def text(self, question: str, style=None):
        print('AI: ' + question)
        if question.startswith('User Story'):
            self.state = 'user_stories'
        elif question.endswith('write "DONE"'):
            self.state = 'DONE'
        return self

    def unsafe_ask(self):
        if self.state == 'user_stories':
            answer = ''
        elif self.state == 'DONE':
            answer = 'DONE'
        else:  # if self.state == 'project_description':
            answer = next(self.answers, '')

        print('User:', answer)
        return answer


@pytest.mark.slow
@pytest.mark.skip(reason="Uses lots of tokens")
def test_end_to_end():
    # Given
    create_tables()
    args = init()
    builtins.print, ipc_client_instance = get_custom_print(args)
    project = Project(args)
    mock_questionary = MockQuestionary([
        'Test App',
        'A web-based chat app',
        # 5 clarifying questions
        'Users can send direct messages to each other but with no group chat functionality',
        'No authentication is required at this stage',
        'Use your best judgement',
        'Use your best judgement',
        'Use your best judgement',
    ])

    # When
    with patch('utils.questionary.questionary', mock_questionary):
        project.start()

