import platform
from unittest.mock import patch, MagicMock, call

import pytest

from helpers.cli import execute_command, terminate_process, run_command_until_success
from helpers.test_Project import create_project

@pytest.mark.xfail()
@patch("helpers.cli.os")
@patch("helpers.cli.subprocess")
def test_terminate_process_not_running(mock_subprocess, mock_os):
    terminate_process(1234, 'not running')

    mock_subprocess.run.assert_not_called()
    mock_os.killpg.assert_not_called()

@patch("helpers.cli.MIN_COMMAND_RUN_TIME", create=True, new=100)
@patch('helpers.cli.run_command')
@patch("helpers.cli.terminate_process")
def test_execute_command_timeout_exit_code(mock_terminate_process, mock_run):
    # Given
    project = create_project()
    command = 'cat'
    timeout = 0.1
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.pid = 1234
    mock_run.return_value = mock_process

    # When
    cli_response, llm_response, exit_code = execute_command(project, command, timeout, force=True)

    # Then
    assert cli_response is not None
    assert llm_response == 'DONE'
    assert exit_code is not None
    mock_terminate_process.assert_called_once_with(1234)


def mock_run_command(command, path, q, q_stderr):
    q.put('hello')
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.pid = 1234
    return mock_process


@patch('helpers.cli.ask_user', return_value='')
@patch('helpers.cli.run_command')
@patch("helpers.cli.terminate_process")
def test_execute_command_enter(mock_terminate_process, mock_run, mock_ask):
    # Given
    project = create_project()
    command = 'echo hello'
    timeout = 1000
    mock_run.side_effect = mock_run_command

    # When
    cli_response, llm_response, exit_code = execute_command(project, command, timeout)

    # Then
    assert 'hello' in cli_response
    assert llm_response == 'DONE'
    assert exit_code == 0
    mock_terminate_process.assert_called_once_with(1234)


@patch('helpers.cli.ask_user', return_value='yes')
@patch('helpers.cli.run_command')
@patch('helpers.cli.terminate_process')
def test_execute_command_yes(mock_terminate_process, mock_run, mock_ask):
    # Given
    project = create_project()
    command = 'echo hello'
    timeout = 1000
    mock_run.side_effect = mock_run_command

    # When
    cli_response, llm_response, exit_code = execute_command(project, command, timeout)

    # Then
    assert 'hello' in cli_response
    assert llm_response == 'DONE'
    assert exit_code == 0
    mock_terminate_process.assert_called_once_with(1234)


@patch('helpers.cli.ask_user', return_value='no')
def test_execute_command_rejected_with_no(mock_ask):
    # Given
    project = create_project()
    command = 'ping www.google.com'
    timeout = 1

    # When
    cli_response, llm_response, exit_code = execute_command(project, command, timeout)

    # Then
    assert cli_response is None
    assert llm_response == 'SKIP'
    assert exit_code is None


@patch('helpers.cli.ask_user', return_value='no, my DNS is not working, ping 8.8.8.8 instead')
def test_execute_command_rejected_with_message(mock_ask):
    # Given
    project = create_project()
    command = 'ping www.google.com'
    timeout = 1

    # When
    cli_response, llm_response, exit_code = execute_command(project, command, timeout)

    # Then
    assert cli_response is None
    assert llm_response == 'no, my DNS is not working, ping 8.8.8.8 instead'
    assert exit_code is None


@patch('helpers.cli.execute_command', return_value=('hello', None, 0))
def test_run_command_until_success(mock_execute):
    # Given
    convo = MagicMock()
    command = 'ping www.google.com'
    timeout = 1

    # When
    result = run_command_until_success(convo, command, timeout)

    # Then
    assert result['success']
    assert result['cli_response'] == 'hello'
    assert convo.send_message.call_count == 1


@patch('helpers.cli.execute_command', return_value=('running...', 'DONE', None))
def test_run_command_until_success_app(mock_execute):
    # Given
    convo = MagicMock()
    command = 'npm run start'
    command_id = 'app'
    timeout = 1000

    # When
    result = run_command_until_success(convo, command, timeout, command_id=command_id)

    # Then
    assert result['success']
    assert result['cli_response'] == 'running...'
    assert convo.send_message.call_count == 0


@patch('helpers.cli.execute_command', return_value=('error', None, 2))
def test_run_command_until_success_error(mock_execute):
    # Given
    convo = MagicMock()
    convo.send_message.return_value = 'NEEDS DEBUGGING'
    convo.agent.debugger.debug.return_value = False
    command = 'ping www.google.com'
    timeout = 1

    # When
    result = run_command_until_success(convo, command, timeout)

    # Then
    assert convo.send_message.call_count == 1
    assert not result['success']
    assert result['cli_response'] == 'error'


@patch('helpers.cli.execute_command', return_value=('hell', 'took longer than 2000ms so I killed it', 0))
def test_run_command_until_success_timed_out(mock_execute):
    # Given
    convo = MagicMock()
    convo.send_message.return_value = 'NEEDS DEBUGGING'
    convo.agent.debugger.debug.return_value = False
    command = 'ping www.google.com'
    timeout = 1

    # When
    result = run_command_until_success(convo, command, timeout)

    # Then
    assert convo.send_message.call_count == 1
    assert not result['success']
    assert result['cli_response'] == 'hell'


@patch('helpers.cli.execute_command', return_value=(None, 'DONE', None))
def test_run_command_until_success_no(mock_execute):
    # Given
    convo = MagicMock()
    command = 'ping www.google.com'
    timeout = 1

    # When
    result = run_command_until_success(convo, command, timeout)

    # Then
    assert result['success']
    assert result['cli_response'] is None
    assert 'user_input' not in result or result['user_input'] is None
    assert convo.send_message.call_count == 0


@patch('helpers.cli.execute_command', return_value=(None, 'no, my DNS is not working, ping 8.8.8.8 instead', None))
def test_run_command_until_success_rejected(mock_execute):
    # Given
    convo = MagicMock()
    command = 'ping www.google.com'
    timeout = 1

    # When
    result = run_command_until_success(convo, command, timeout)

    # Then
    assert not result['success']
    assert 'cli_response' not in result or result['cli_response'] is None
    assert result['user_input'] == 'no, my DNS is not working, ping 8.8.8.8 instead'
    assert convo.send_message.call_count == 0
