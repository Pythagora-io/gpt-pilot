import psutil
import subprocess
import os
import signal
import threading
import queue
import time
import platform
from typing import Dict, Union

from logger.logger import logger
from utils.style import color_green, color_red, color_yellow_bold
from utils.ignore import IgnoreMatcher
from database.database import save_command_run
from helpers.exceptions import TooDeepRecursionError
from helpers.exceptions import TokenLimitError
from helpers.exceptions import CommandFinishedEarly
from prompts.prompts import ask_user
from const.code_execution import MIN_COMMAND_RUN_TIME, MAX_COMMAND_RUN_TIME, MAX_COMMAND_OUTPUT_LENGTH
from const.messages import AFFIRMATIVE_ANSWERS, NEGATIVE_ANSWERS

interrupted = False

running_processes: Dict[str, tuple[str, int]] = {}
"""Holds a list of (command, process ID)s, mapped to the `command_id` provided in the call to `execute_command()`."""


def enqueue_output(out, q):
    for line in iter(out.readline, ''):
        if interrupted:  # Check if the flag is set
            break
        q.put(line)
    out.close()


def run_command(command, root_path, q_stdout, q_stderr) -> subprocess.Popen:
    """
    Execute a command in a subprocess.

    Args:
        command (str): The command to run.
        root_path (str): The directory in which to run the command.
        q_stdout (Queue): A queue to capture stdout.
        q_stderr (Queue): A queue to capture stderr.

    Returns:
        subprocess.Popen: The subprocess object.
    """
    logger.info(f'Running `{command}` on {platform.system()}')
    if platform.system() == 'Windows':  # Check the operating system
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=root_path
        )
    else:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,  # Use os.setsid only for Unix-like systems
            cwd=root_path
        )

    t_stdout = threading.Thread(target=enqueue_output, args=(process.stdout, q_stdout))
    t_stderr = threading.Thread(target=enqueue_output, args=(process.stderr, q_stderr))
    t_stdout.daemon = True
    t_stderr.daemon = True
    t_stdout.start()
    t_stderr.start()
    return process


def terminate_named_process(command_id: str) -> None:
    if command_id in running_processes:
        terminate_process(running_processes[command_id][1], command_id)


def terminate_running_processes():
    for command_id in list(running_processes.keys()):
        terminate_process(running_processes[command_id][1], command_id)


def term_proc_windows(pid: int):
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)])
    except subprocess.CalledProcessError as e:
        logger.error(f'Error while terminating process: {e}')


def term_proc_unix_like(pid: int):
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError as e:
        logger.error(f'Error while terminating process: {e}')


def is_process_running(pid: int) -> bool:
    """Check if there is a running process with the given PID."""
    try:
        # psutil.NoSuchProcess will be raised if the process doesn't exist
        process = psutil.Process(pid)
        return process.is_running()
    except psutil.NoSuchProcess:
        return False


def terminate_process(pid: int, name=None) -> None:
    # todo refactor terminate_process() using psutil for all OS. Check/terminate child processes and test on all OS
    if name is None:
        name = ''

    if not is_process_running(pid):
        logger.info('Process "%s" (pid: %s) is not running. Skipping termination.', name, pid)
        # Also remove from running_processes if not running
        for command_id, process_info in list(running_processes.items()):
            if process_info[1] == pid:
                del running_processes[command_id]
        return

    logger.info('Terminating process "%s" (pid: %s)', name, pid)
    if platform.system() == "Windows":
        term_proc_windows(pid)
    else:  # Unix-like systems
        term_proc_unix_like(pid)

    try:
        # Wait for the process to terminate
        process = psutil.Process(pid)
        process.wait(timeout=10)  # Adjust the timeout as necessary
    except psutil.NoSuchProcess:
        logger.info("Process already terminated.")
    except psutil.TimeoutExpired:
        logger.warning("Timeout expired while waiting for process to terminate.")
    except Exception as e:
        logger.error(f"Error waiting for process termination: {e}")

    for command_id in list(running_processes.keys()):
        if running_processes[command_id][1] == pid:
            del running_processes[command_id]


def read_queue_line(q, stdout=True):
    try:
        line = q.get_nowait()
    except queue.Empty:
        return ''

    if stdout:
        print(color_green('CLI OUTPUT:') + line, end='')
        logger.info('CLI OUTPUT: ' + line)
        # if success_message is not None and success_message in line:
        #     logger.info('Success message found: %s', success_message)
        #     # break # TODO background_command - this is if we want to leave command running in background but sometimes processes keep hanging and terminal gets bugged, also if we do that we have to change user messages to make it clear that there is command running in background
        #     raise CommandFinishedEarly()

    if not stdout:  # stderr
        print(color_red('CLI ERROR:') + line, end='')
        logger.error('CLI ERROR: ' + line)

    return line


def read_remaining_queue(q, stdout=True):
    output = ''
    while not q.empty():
        output += read_queue_line(q, stdout)

    return output


def execute_command(project, command, timeout=None, success_message=None, command_id: str = None, force=False) \
        -> (str, str, int):
    """
    Execute a command and capture its output.

    Args:
        project: The project associated with the command.
        command (str): The command to run.
        timeout (int, optional): The maximum execution time in milliseconds. Default is None.
        success_message: A message to look for in the output of the command to determine if successful or not.
        command_id (str, optional): A unique identifier assigned by the LLM, can be used to terminate the process.
        force (bool, optional): Whether to execute the command without confirmation. Default is False.
    Returns:
        cli_response (str): The command output
                            or: `None` if user did not authorise the command to run
        done_or_error_response (str): 'DONE' if 'no', 'skip' or `success_message` matched.
                            Otherwise, if `cli_response` is None, user's response to "Can I executed".
                            If `cli_response` not None: 'was interrupted by user', 'timed out' or `None` - caller should send `cli_response` to LLM
        exit_code (int): The exit code of the process.
    """
    project.finish_loading()
    if timeout is not None:
        if timeout < 0:
            timeout = None
        else:
            if timeout < 1000:
                timeout *= 1000

            timeout = min(max(timeout, MIN_COMMAND_RUN_TIME), MAX_COMMAND_RUN_TIME)

    if not force:
        print(color_yellow_bold('\n--------- EXECUTE COMMAND ----------'))
        question = f'Can I execute the command: `{color_yellow_bold(command)}`'
        if timeout is not None:
            question += f' with {timeout}ms timeout?'
        else:
            question += '?'

        print('yes/no', type='buttons-only')
        logger.info('--------- EXECUTE COMMAND ---------- : %s', question)
        answer = ask_user(project, question, False, hint='If yes, just press ENTER. Otherwise, type "no" but it will be processed as successfully executed.')
        # TODO can we use .confirm(question, default='yes').ask()  https://questionary.readthedocs.io/en/stable/pages/types.html#confirmation
        print('answer: ' + answer)
        if answer.lower() in NEGATIVE_ANSWERS:
            return None, 'SKIP', None
        elif answer.lower() not in AFFIRMATIVE_ANSWERS:
            # "That's not going to work, let's do X instead"
            #       https://github.com/Pythagora-io/gpt-pilot/issues/198
            #       https://github.com/Pythagora-io/gpt-pilot/issues/43#issuecomment-1756352056
            # TODO: https://github.com/Pythagora-io/gpt-pilot/issues/122
            return None, answer, None

    # TODO when a shell built-in commands (like cd or source) is executed, the output is not captured properly - this will need to be changed at some point
    if platform.system() != 'Windows' and ("cd " in command or "source " in command):
        command = f"bash -c '{command}'"

    project.command_runs_count += 1

    return_value = None
    done_or_error_response = None

    q_stderr = queue.Queue()
    q = queue.Queue()
    process = run_command(command, project.root_path, q, q_stderr)

    if command_id is not None:
        terminate_named_process(command_id)
        # TODO: We want to be able to send the initial stdout/err to the LLM, but it would also be handy to log ongoing output to a log file, named after `command_id`. Terminating an existing process with the same ID should reset the log file
        running_processes[command_id] = (command, process.pid)

    output = ''
    stderr_output = ''
    start_time = time.time()

    # Note: If we don't need to log the output in real-time, we can remove q, q_stderr, the threads and this while loop.
    # if timeout is not None:
    #     timeout /= 1000
    # output, stderr_output = process.communicate(timeout=timeout)

    try:
        while True:
            elapsed_time = time.time() - start_time
            time.sleep(0.1)  # TODO this shouldn't be used
            # if timeout is not None:
            #     # TODO: print to IPC using a different message type so VS Code can ignore it or update the previous value
            #     print(color_white_bold(f'\rt: {round(elapsed_time * 1000)}ms : '), end='', flush=True)

            # If timeout is reached, kill the process
            if timeout is not None and elapsed_time * 1000 > timeout:
                if command_id is not None:
                    logger.info(f'Process "{command_id}" running after timeout as pid: {process.pid}')
                    break

                raise TimeoutError("Command exceeded the specified timeout.")

            output += read_queue_line(q)
            stderr_output += read_queue_line(q_stderr, False)

            # Check if process has finished
            if process.poll() is not None:
                logger.info('process exited with return code: %d', process.returncode)
                if command_id is not None:
                    del running_processes[command_id]

                output += read_remaining_queue(q)
                stderr_output += read_remaining_queue(q_stderr, False)
                break

    except (KeyboardInterrupt, TimeoutError, CommandFinishedEarly) as e:
        if isinstance(e, KeyboardInterrupt):
            print('\nCTRL+C detected. Stopping command execution...')
            logger.info('CTRL+C detected. Stopping command execution...')
            done_or_error_response = 'was interrupted by user'
        elif isinstance(e, TimeoutError):
            print('\nTimeout detected. Stopping command execution...')
            logger.warning('Timeout detected. Stopping command execution...')
            done_or_error_response = f'took longer than {timeout}ms so I killed it'
        elif isinstance(e, CommandFinishedEarly):
            print('\nCommand finished before timeout. Handling early completion...')
            logger.info('Command finished before timeout. Handling early completion...')
            done_or_error_response = 'DONE'

    finally:
        done_or_error_response = 'DONE'  # Todo remove if we want to have different responses
        terminate_process(process.pid)  # TODO: background_command - remove this is if we want to leave command running in background, look todo above
        # update the return code
        process.poll()

    elapsed_time = time.time() - start_time
    logger.info(f'`{command}` took {round(elapsed_time * 1000)}ms to execute.')

    if return_value is None:
        return_value = ''
        if stderr_output != '':
            return_value = 'stderr:\n```\n' + stderr_output[0:MAX_COMMAND_OUTPUT_LENGTH] + '\n```\n'
        return_value += 'stdout:\n```\n' + output[-MAX_COMMAND_OUTPUT_LENGTH:] + '\n```'

    save_command_run(project, command, return_value, done_or_error_response, process.returncode)

    return return_value, done_or_error_response, process.returncode


def check_if_command_successful(convo, command, cli_response, response, exit_code, additional_message=None,
                                task_steps=None, step_index=None):
    if cli_response is not None:
        logger.info(f'`{command}` ended with exit code: {exit_code}')
        if exit_code is None:
            # todo this should never happen! process is still running, see why and now we want to handle it
            print(color_red(f'Process for command {command} still running.'))
            response = 'DONE'
        else:
            response = convo.send_message('dev_ops/ran_command.prompt',
                                          {
                                              'cli_response': cli_response,
                                              'error_response': response,
                                              'command': command,
                                              'additional_message': additional_message,
                                              'exit_code': exit_code,
                                              'task_steps': task_steps,
                                              'step_index': step_index,
                                          })
            logger.debug(f'LLM response to ran_command.prompt: {response}')
            if response == 'DONE':
                convo.remove_last_x_messages(2)

    return response

def build_directory_tree(path, prefix='', root_path=None) -> str:
    """Build the directory tree structure in a simplified format.

    :param path: The starting directory path.
    :param prefix: Prefix for the current item, used for recursion.
    :param root_path: The root directory path.
    :return: A string representation of the directory tree.
    """
    output = ""
    indent = '  '

    if root_path is None:
        root_path = path

    matcher = IgnoreMatcher(root_path=root_path)

    if os.path.isdir(path):
        if root_path == path:
            output += '/'
        else:
            dir_name = os.path.basename(path)
            output += f'{prefix}/{dir_name}'

        # List items in the directory
        items = os.listdir(path)
        dirs = []
        files = []
        for item in items:
            item_path = os.path.join(path, item)
            if matcher.ignore(item_path):
                continue
            if os.path.isdir(item_path):
                dirs.append(item)
            elif os.path.isfile(item_path):
                files.append(item)
        dirs.sort()
        files.sort()

        if dirs:
            output += '\n'
            for index, dir_item in enumerate(dirs):
                item_path = os.path.join(path, dir_item)
                new_prefix = prefix + indent  # Updated prefix for recursion
                output += build_directory_tree(item_path, new_prefix, root_path)

            if files:
                output += f"{prefix}  {', '.join(files)}\n"

        elif files:
            output += f": {', '.join(files)}\n"
        else:
            output += '\n'

    return output


def execute_command_and_check_cli_response(convo, command: dict, task_steps=None, step_index=None):
    """
    Execute a command and check its CLI response.

    Args:
        convo (AgentConvo): The conversation object.
        command (dict):
          ['command'] (str): The command to run.
          ['timeout'] (int): The maximum execution time in milliseconds.
        task_steps (list, optional): The steps of the current task. Default is None.
        step_index (int, optional): The index of the current step. Default is None.


    Returns:
        tuple: A tuple containing the CLI response and the agent's response.
            - cli_response (str): The command output.
            - response (str): 'DONE' or 'BUG'.
                If `cli_response` is None, user's response to "Can I execute...".
    """
    # TODO: Prompt mentions `command` could be `INSTALLED` or `NOT_INSTALLED`, where is this handled?
    command_id = command['command_id'] if 'command_id' in command else None
    cli_response, response, exit_code = execute_command(convo.agent.project,
                                                        command['command'],
                                                        timeout=command['timeout'],
                                                        command_id=command_id)

    response = check_if_command_successful(convo, command['command'], cli_response, response, exit_code,
                                           task_steps=task_steps, step_index=step_index)
    return cli_response, response


def run_command_until_success(convo, command,
                              timeout: Union[int, None],
                              command_id: Union[str, None] = None,
                              success_message=None,
                              additional_message=None,
                              force=False,
                              return_cli_response=False,
                              success_with_cli_response=False,
                              is_root_task=False,
                              task_steps=None,
                              step_index=None):
    """
    Run a command until it succeeds or reaches a timeout.

    Args:
        convo (AgentConvo): The conversation object.
        command (str): The command to run.
        timeout (int): The maximum execution time in milliseconds.
        command_id: A name for the process.
                      If `timeout` is not provided, can be used to terminate the process.
        success_message: A message to look for in the output of the command to determine if successful or not.
        additional_message (str, optional): Additional message to include in the "I ran the command..." prompt.
        force (bool, optional): Whether to execute the command without confirmation. Default is False.
        return_cli_response (bool, optional): If True, may raise TooDeepRecursionError(cli_response)
        success_with_cli_response (bool, optional): If True, simply send the cli_response back to the caller without checking with LLM.
                                                    The LLM has asked to see the output and may update the task step list.
        is_root_task (bool, optional): If True and TokenLimitError is raised, will call `convo.load_branch(reset_branch_id)`
        task_steps (list, optional): The steps of the current task. Default is None.
        step_index (int, optional): The index of the current step. Default is None.

    Returns:
        - 'success': bool,
        - 'cli_response': ```stdout: <stdout> stderr: <stderr>```
        - 'user_input': `None` or user's objection to running the command
    """
    cli_response, response, exit_code = execute_command(convo.agent.project,
                                                        command,
                                                        timeout=timeout,
                                                        success_message=success_message,
                                                        command_id=command_id,
                                                        force=force)

    if success_with_cli_response and cli_response is not None:
        return {'success': True, 'cli_response': cli_response}

    if response == 'SKIP':
        return {'success': True, 'user_input': response}

    if cli_response is None and response != 'DONE':
        return {'success': False, 'user_input': response}

    response = check_if_command_successful(convo, command, cli_response, response, exit_code, additional_message,
                                           task_steps=task_steps, step_index=step_index)
    if response:
        response = response.strip()

    if response != 'DONE':
        # 'BUG'
        print(color_red('Got incorrect CLI response:'))
        print(cli_response)
        print(color_red('-------------------'))

        reset_branch_id = convo.save_branch()
        while True:
            try:
                # This catch is necessary to return the correct value (cli_response) to continue development function so
                # the developer can debug the appropriate issue
                # this snippet represents the first entry point into debugging recursion because of return_cli_response
                success = convo.agent.debugger.debug(convo, {
                    'command': command,
                    'timeout': timeout,
                    'command_id': command_id,
                    'success_message': success_message,
                },user_input=cli_response, is_root_task=is_root_task, ask_before_debug=True, task_steps=task_steps, step_index=step_index)
                return {'success': success, 'cli_response': cli_response}
            except TooDeepRecursionError as e:
                # this is only to put appropriate message in the response after TooDeepRecursionError is raised
                raise TooDeepRecursionError(cli_response) if return_cli_response else e
            except TokenLimitError as e:
                if is_root_task:
                    convo.load_branch(reset_branch_id)
                else:
                    raise e
    else:
        return {'success': True, 'cli_response': cli_response}
