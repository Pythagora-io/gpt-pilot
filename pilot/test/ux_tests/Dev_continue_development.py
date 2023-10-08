import pytest
from unittest.mock import patch

from helpers.AgentConvo import AgentConvo
from helpers.agents import Developer
from .utils import create_project
from helpers.cli import terminate_running_processes
from test.mock_questionary import MockQuestionary


@pytest.mark.ux_test
@patch('utils.questionary.get_saved_user_input')
@patch('helpers.cli.get_saved_command_run')
@patch('helpers.AgentConvo.get_saved_development_step')
@patch('helpers.AgentConvo.save_development_step')
def test_continue_development(mock_4, mock_3, mock_2, mock_1):
    # Given
    project = create_project('continue_development', 'hello_world_server')
    # execute_command(project, 'npm install', 13000)

    developer = Developer(project)
    project.developer = developer
    convo = AgentConvo(developer)
    convo.load_branch = lambda last_branch_name: None
    developer.run_command = 'node server.js'

    # Note: uncomment the following 2 lines and indent the remaining lines when debugging without console input
    mock_questionary = MockQuestionary(['r', 'continue'])
    with patch('utils.questionary.questionary', mock_questionary):

        # When
        # `continue_development` calls `run_command_until_success()` if the user types "r"
        developer.continue_development(convo, 'branch_name', 'The web page should say "Hello, World!"')
        print('end of "continue_development" scenario')

    terminate_running_processes()
