import subprocess
import os
import signal
import threading
import queue
import time
import platform
from typing import Dict, Union

from logger.logger import logger
from utils.style import color_yellow, color_green, color_red, color_yellow_bold, color_white_bold
from database.database import get_saved_command_run, save_command_run
from helpers.exceptions.TooDeepRecursionError import TooDeepRecursionError
from helpers.exceptions.TokenLimitError import TokenLimitError
from prompts.prompts import ask_user
from const.code_execution import MIN_COMMAND_RUN_TIME, MAX_COMMAND_RUN_TIME, MAX_COMMAND_OUTPUT_LENGTH

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


def terminate_process(pid: int, name=None) -> None:
    if name is None:
        name = ''
    logger.info('Terminating process "%s" (pid: %s)', name, pid)

    if platform.system() == "Windows":
        term_proc_windows(pid)
    else:  # Unix-like systems
        term_proc_unix_like(pid)

    for command_id in list(running_processes.keys()):
        if running_processes[command_id][1] == pid:
            del running_processes[command_id]


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

        answer = ask_user(project, question, False, hint='If yes, just press ENTER')
        # TODO can we use .confirm(question, default='yes').ask()  https://questionary.readthedocs.io/en/stable/pages/types.html#confirmation
        print('answer: ' + answer)
        if answer.lower() in ['no', 'skip']:
            return None, 'DONE', None
        elif answer.lower() not in ['', 'yes', 'ok', 'okay', 'sure']:
            # "That's not going to work, let's do X instead"
            #       https://github.com/Pythagora-io/gpt-pilot/issues/198
            #       https://github.com/Pythagora-io/gpt-pilot/issues/43#issuecomment-1756352056
            # TODO: https://github.com/Pythagora-io/gpt-pilot/issues/122
            return None, answer, None

    # TODO when a shell built-in commands (like cd or source) is executed, the output is not captured properly - this will need to be changed at some point
    if platform.system() != 'Windows' and ("cd " in command or "source " in command):
        command = "bash -c '" + command + "'"

    project.command_runs_count += 1
    command_run = get_saved_command_run(project, command)
    if command_run is not None and project.skip_steps:
        # if we do, use it
        project.checkpoints['last_command_run'] = command_run
        print(color_yellow(f'Restoring command run response id {command_run.id}:\n```\n{command_run.cli_response}```'))
        return command_run.cli_response, None, None

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
            # if timeout is not None:
            #     # TODO: print to IPC using a different message type so VS Code can ignore it or update the previous value
            #     print(color_white_bold(f'\rt: {round(elapsed_time * 1000)}ms : '), end='', flush=True)

            # Check if process has finished
            if process.poll() is not None:
                logger.info('process exited with return code: %d', process.returncode)
                if command_id is not None:
                    del running_processes[command_id]
                # Get remaining lines from the queue
                time.sleep(0.1)  # TODO this shouldn't be used
                while not q.empty():
                    output_line = q.get_nowait()
                    if output_line not in output:
                        print(color_green('CLI OUTPUT:') + output_line, end='')
                        logger.info('CLI OUTPUT: ' + output_line)
                        output += output_line
                break

            # If timeout is reached, kill the process
            if timeout is not None and elapsed_time * 1000 > timeout:
                if command_id is not None:
                    logger.info(f'Process "{command_id}" running after timeout as pid: {process.pid}')
                    break

                raise TimeoutError("Command exceeded the specified timeout.")
                # os.killpg(process.pid, signal.SIGKILL)
                # break

            try:
                line = q.get_nowait()
            except queue.Empty:
                line = None

            if line:
                output += line
                print(color_green('CLI OUTPUT:') + line, end='')
                logger.info('CLI OUTPUT: ' + line)
                if success_message is not None and success_message in line:
                    logger.info('Success message found: %s', success_message)
                    done_or_error_response = 'DONE'
                    break

            # Read stderr
            try:
                stderr_line = q_stderr.get_nowait()
            except queue.Empty:
                stderr_line = None

            if stderr_line:
                stderr_output += stderr_line
                print(color_red('CLI ERROR:') + stderr_line, end='')  # Print with different color for distinction
                logger.error('CLI ERROR: ' + stderr_line)

    except (KeyboardInterrupt, TimeoutError) as e:
        if isinstance(e, KeyboardInterrupt):
            print('\nCTRL+C detected. Stopping command execution...')
            logger.info('CTRL+C detected. Stopping command execution...')
            done_or_error_response = 'was interrupted by user'
        else:
            print('\nTimeout detected. Stopping command execution...')
            logger.warn('Timeout detected. Stopping command execution...')
            done_or_error_response = f'took longer than {timeout}ms so I killed it'

        terminate_process(process.pid)
        # update the returncode
        process.poll()

    elapsed_time = time.time() - start_time
    logger.info(f'`{command}` took {round(elapsed_time * 1000)}ms to execute.')

    # stderr_output = ''
    # while not q_stderr.empty():
    #     stderr_output += q_stderr.get_nowait()

    if return_value is None:
        return_value = ''
        if stderr_output != '':
            return_value = 'stderr:\n```\n' + stderr_output[0:MAX_COMMAND_OUTPUT_LENGTH] + '\n```\n'
        return_value += 'stdout:\n```\n' + output[-MAX_COMMAND_OUTPUT_LENGTH:] + '\n```'

    save_command_run(project, command, return_value)

    return return_value, done_or_error_response, process.returncode


def build_directory_tree(path, prefix='', is_root=True, ignore=None):
    """Build the directory tree structure in a simplified format.

    Args:
    - path: The starting directory path.
    - prefix: Prefix for the current item, used for recursion.
    - is_root: Flag to indicate if the current item is the root directory.
    - ignore: a list of directories to ignore

    Returns:
    - A string representation of the directory tree.
    """
    output = ""
    indent = '  '

    if os.path.isdir(path):
        dir_name = os.path.basename(path)
        if is_root:
            output += '/'
        else:
            output += f'{prefix}/{dir_name}'

        # List items in the directory
        items = os.listdir(path)
        dirs = [item for item in items if os.path.isdir(os.path.join(path, item)) and item not in ignore]
        files = [item for item in items if os.path.isfile(os.path.join(path, item))]
        dirs.sort()
        files.sort()

        if dirs:
            output += '\n'
            for index, dir_item in enumerate(dirs):
                item_path = os.path.join(path, dir_item)
                output += build_directory_tree(item_path, prefix + indent, is_root=False, ignore=ignore)

            if files:
                output += f"{prefix}  {', '.join(files)}\n"

        elif files:
            output += f": {', '.join(files)}\n"
        else:
            output += '\n'

    return output


def res_for_build_directory_tree(path, files=None):
    return ' - ' + files[os.path.basename(path)].description + ' ' if files and os.path.basename(path) in files else ''


def build_directory_tree_with_descriptions(path, prefix="", ignore=None, is_last=False, files=None):
    """Build the directory tree structure in tree-like format.
    Args:
    - path: The starting directory path.
    - prefix: Prefix for the current item, used for recursion.
    - ignore: List of directory names to ignore.
    - is_last: Flag to indicate if the current item is the last in its parent directory.
    Returns:
    - A string representation of the directory tree.
    """
    ignore |= []
    if os.path.basename(path) in ignore:
        return ""
    output = ""
    indent = '|   ' if not is_last else '    '
    # It's a directory, add its name to the output and then recurse into it
    output += prefix + "|-- " + os.path.basename(path) + res_for_build_directory_tree(path, files) + "/\n"
    if os.path.isdir(path):
        # List items in the directory
        items = os.listdir(path)
        for index, item in enumerate(items):
            item_path = os.path.join(path, item)
            output += build_directory_tree(item_path, prefix + indent, ignore, index == len(items) - 1, files)
    return output


def execute_command_and_check_cli_response(convo, command: dict):
    """
    Execute a command and check its CLI response.

    Args:
        convo (AgentConvo): The conversation object.
        command (dict):
          ['command'] (str): The command to run.
          ['timeout'] (int): The maximum execution time in milliseconds.


    Returns:
        tuple: A tuple containing the CLI response and the agent's response.
            - cli_response (str): The command output.
            - response (str): 'DONE' or 'NEEDS_DEBUGGING'.
                If `cli_response` is None, user's response to "Can I execute...".
    """
    # TODO: Prompt mentions `command` could be `INSTALLED` or `NOT_INSTALLED`, where is this handled?
    command_id = command['command_id'] if 'command_id' in command else None
    cli_response, response, exit_code = execute_command(convo.agent.project,
                                                        command['command'],
                                                        timeout=command['timeout'],
                                                        command_id=command_id)
    if cli_response is not None:
        if exit_code is None:
            response = 'DONE'
        elif response != 'DONE':
            # "I ran the command `{{command}}` -> {{ exit_code }}, {{ error_response }}, output: {{ cli_response }
            # respond with 'DONE' or 'NEEDS_DEBUGGING'"
            response = convo.send_message('dev_ops/ran_command.prompt',
                                          {
                                              'cli_response': cli_response,
                                              'error_response': response,
                                              'command': command['command'],
                                              'exit_code': exit_code,
                                          })
    return cli_response, response


def run_command_until_success(convo, command,
                              timeout: Union[int, None],
                              command_id: Union[str, None] = None,
                              success_message=None,
                              additional_message=None,
                              force=False,
                              return_cli_response=False,
                              success_with_cli_response=False,
                              is_root_task=False):
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

    if cli_response is None and response != 'DONE':
        return {'success': False, 'user_input': response}

    if cli_response is not None:
        logger.info(f'`{command}` ("{command_id}") exit code: {exit_code}')
        if exit_code is None and command_id is not None:
            # process is still running
            response = 'DONE'
        elif response != 'DONE':
            # "I ran the command and the output was... respond with 'DONE' or 'NEEDS_DEBUGGING'"
            response = convo.send_message('dev_ops/ran_command.prompt',
                                          {
                                              'cli_response': cli_response,
                                              'error_response': response,
                                              'command': command,
                                              'additional_message': additional_message,
                                              'exit_code': exit_code,
                                          })
            logger.debug(f'LLM response: {response}')

    if response != 'DONE':
        # 'NEEDS_DEBUGGING'
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
                })
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
