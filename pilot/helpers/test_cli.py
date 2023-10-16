from unittest.mock import patch
from helpers.cli import execute_command, terminate_process
from helpers.test_Project import create_project


def test_terminate_process_not_running():
    terminate_process(999999999, 'not running')
    assert True


@patch('helpers.cli.get_saved_command_run')
def test_execute_command_timeout_exit_code(mock_get_saved_command):
    # Given
    project = create_project()
    command = 'ping www.google.com'
    timeout = 1

    # When
    cli_response, llm_response, exit_code = execute_command(project, command, timeout, force=True)

    # Then
    assert llm_response is None
    assert exit_code is not None
