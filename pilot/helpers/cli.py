import subprocess
import os
import signal
import threading
import queue
import time
import platform
from typing import Dict, Union

from logger.logger import logger
from utils.style import yellow, green, red, yellow_bold, white_bold
from database.database import get_saved_command_run, save_command_run
from helpers.exceptions.TooDeepRecursionError import TooDeepRecursionError
from helpers.exceptions.TokenLimitError import TokenLimitError
from prompts.prompts import ask_user
from const.code_execution import MIN_COMMAND_RUN_TIME, MAX_COMMAND_RUN_TIME, MAX_COMMAND_OUTPUT_LENGTH

interrupted = False

running_processes: Dict[str, tuple[str, int]] = {}
"""Holds a list of (command, process ID)s, mapped to the `process_name` provided in the call to `execute_command()`."""


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


def terminate_named_process(process_name: str) -> None:
    if process_name in running_processes:
        terminate_process(running_processes[process_name][1], process_name)


def terminate_running_processes():
    for process_name in list(running_processes.keys()):
        terminate_process(running_processes[process_name][1], process_name)


def terminate_process(pid: int, name=None) -> None:
    if name is None:
        logger.info('Terminating process %s', pid)
    else:
        logger.info('Terminating process "%s" (pid: %s)', name, pid)

    if platform.system() == "Windows":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)])
        except subprocess.CalledProcessError as e:
            logger.error(f'Error while terminating process: {e}')
    else:  # Unix-like systems
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError as e:
            logger.error(f'Error while terminating process: {e}')

    for process_name in list(running_processes.keys()):
        if running_processes[process_name][1] == pid:
            del running_processes[process_name]


def execute_command(project, command, timeout=None, success_message=None, process_name: str = None, force=False) \
        -> (str, str, int):
    """
    Execute a command and capture its output.

    Args:
        project: The project associated with the command.
        command (str): The command to run.
        timeout (int, optional): The maximum execution time in milliseconds. Default is None.
        success_message: A message to look for in the output of the command to determine if successful or not.
        process_name (str, optional): A name for the process.
                            If `timeout` is not provided, can be used to terminate the process.
        force (bool, optional): Whether to execute the command without confirmation. Default is False.

    Returns:
        cli_response (str): The command output
                            or: '', 'DONE' if user answered 'no' or 'skip'
        llm_response (str): 'DONE' if 'no', 'skip' or `success_message` matched.
                            Otherwise `None` - caller should send `cli_response` to LLM
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
        print(yellow_bold(f'\n--------- EXECUTE COMMAND ----------'))
        question = f'Can I execute the command: `{yellow_bold(command)}`'
        if timeout is not None:
            question += f' with {timeout}ms timeout?'
        else:
            question += '?'

        answer = ask_user(project, question, False, hint='If yes, just press ENTER')

        # TODO: I think AutoGPT allows other feedback here, like:
        #       "That's not going to work, let's do X instead"
        #       We don't explicitly make "no" or "skip" options to the user
        #       see https://github.com/Pythagora-io/gpt-pilot/issues/122
        print('answer: ' + answer)
        if answer == 'no':
            return '', 'DONE', None
        elif answer == 'skip':
            return '', 'DONE', None

    # TODO when a shell built-in commands (like cd or source) is executed, the output is not captured properly - this will need to be changed at some point
    # TODO: Windows support
    if "cd " in command or "source " in command:
        command = "bash -c '" + command + "'"

    project.command_runs_count += 1
    command_run = get_saved_command_run(project, command)
    if command_run is not None and project.skip_steps:
        # if we do, use it
        project.checkpoints['last_command_run'] = command_run
        print(yellow(f'Restoring command run response id {command_run.id}:\n```\n{command_run.cli_response}```'))
        return command_run.cli_response, None, None

    return_value = None
    was_success = None

    q_stderr = queue.Queue()
    q = queue.Queue()
    pid_container = [None]
    process = run_command(command, project.root_path, q, q_stderr)

    if process_name is not None:
        terminate_named_process(process_name)
        running_processes[process_name] = (command, process.pid)

    output = ''
    stderr_output = ''
    start_time = time.time()
    interrupted = False

    # Note: If we don't need to log the output in real-time, we can remove q, q_stderr, the threads and this while loop.
    # if timeout is not None:
    #     timeout /= 1000
    # output, stderr_output = process.communicate(timeout=timeout)

    try:
        while True:
            elapsed_time = time.time() - start_time
            # if timeout is not None:
            #     # TODO: print to IPC using a different message type so VS Code can ignore it or update the previous value
            #     print(white_bold(f'\rt: {round(elapsed_time * 1000)}ms : '), end='', flush=True)

            # Check if process has finished
            if process.poll() is not None:
                # Get remaining lines from the queue
                time.sleep(0.1)  # TODO this shouldn't be used
                while not q.empty():
                    output_line = q.get_nowait()
                    if output_line not in output:
                        print(green('CLI OUTPUT:') + output_line, end='')
                        logger.info('CLI OUTPUT: ' + output_line)
                        output += output_line
                break

            # If timeout is reached, kill the process
            if timeout is not None and elapsed_time * 1000 > timeout:
                if process_name is not None:
                    logger.info(f'Process "{process_name}" running after timeout as pid: {process.pid}')
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
                print(green('CLI OUTPUT:') + line, end='')
                logger.info('CLI OUTPUT: ' + line)
                if success_message is not None and success_message in line:
                    logger.info('Success message found: %s', success_message)
                    was_success = True
                    break

            # Read stderr
            try:
                stderr_line = q_stderr.get_nowait()
            except queue.Empty:
                stderr_line = None

            if stderr_line:
                stderr_output += stderr_line
                print(red('CLI ERROR:') + stderr_line, end='')  # Print with different color for distinction
                logger.error('CLI ERROR: ' + stderr_line)

    except (KeyboardInterrupt, TimeoutError) as e:
        interrupted = True
        if isinstance(e, KeyboardInterrupt):
            print('\nCTRL+C detected. Stopping command execution...')
            logger.info('CTRL+C detected. Stopping command execution...')
        else:
            print('\nTimeout detected. Stopping command execution...')
            logger.warn('Timeout detected. Stopping command execution...')

        was_success = False
        terminate_process(process.pid)

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

    return return_value, 'DONE' if was_success else None, process.returncode


def build_directory_tree(path, prefix="", ignore=None, is_last=False, files=None, add_descriptions=False):
    """Build the directory tree structure in tree-like format.

    Args:
    - path: The starting directory path.
    - prefix: Prefix for the current item, used for recursion.
    - ignore: List of directory names to ignore.
    - is_last: Flag to indicate if the current item is the last in its parent directory.

    Returns:
    - A string representation of the directory tree.
    """
    if ignore is None:
        ignore = []

    if os.path.basename(path) in ignore:
        return ""

    output = ""
    indent = '|   ' if not is_last else '    '

    if os.path.isdir(path):
        # It's a directory, add its name to the output and then recurse into it
        output += prefix + "|-- " + os.path.basename(path) + ((' - ' + files[os.path.basename(path)].description + ' ' if files and os.path.basename(path) in files and add_descriptions else '')) + "/\n"

        # List items in the directory
        items = os.listdir(path)
        for index, item in enumerate(items):
            item_path = os.path.join(path, item)
            output += build_directory_tree(item_path, prefix + indent, ignore, index == len(items) - 1, files, add_descriptions)

    else:
        # It's a file, add its name to the output
        output += prefix + "|-- " + os.path.basename(path) + ((' - ' + files[os.path.basename(path)].description + ' ' if files and os.path.basename(path) in files and add_descriptions else '')) + "\n"

    return output


def execute_command_and_check_cli_response(command, timeout, convo):
    """
    Execute a command and check its CLI response.

    Args:
        command (str): The command to run.
        timeout (int): The maximum execution time in milliseconds.
        convo (AgentConvo): The conversation object.

    Returns:
        tuple: A tuple containing the CLI response and the agent's response.
            - cli_response (str): The command output.
            - llm_response (str): 'DONE' or 'NEEDS_DEBUGGING'
    """
    # TODO: Prompt mentions `command` could be `INSTALLED` or `NOT_INSTALLED`, where is this handled?
    cli_response, llm_response, exit_code = execute_command(convo.agent.project, command, timeout=timeout)
    if llm_response is None:
        llm_response = convo.send_message('dev_ops/ran_command.prompt',
            {
                'cli_response': cli_response,
                'command': command
            })
    return cli_response, llm_response


def run_command_until_success(convo, command,
                              timeout: Union[int, None],
                              process_name: Union[str, None] = None,
                              success_message=None,
                              additional_message=None,
                              force=False,
                              return_cli_response=False,
                              is_root_task=False):
    """
    Run a command until it succeeds or reaches a timeout.

    Args:
        convo (AgentConvo): The conversation object.
        command (str): The command to run.
        timeout (int): The maximum execution time in milliseconds.
        process_name: A name for the process.
                      If `timeout` is not provided, can be used to terminate the process.
        success_message: A message to look for in the output of the command to determine if successful or not.
        additional_message (str, optional): Additional message to include in the response.
        force (bool, optional): Whether to execute the command without confirmation. Default is False.
        return_cli_response (bool, optional): If True, may raise TooDeepRecursionError(cli_response)
        is_root_task (bool, optional): If True and TokenLimitError is raised, will call `convo.load_branch(reset_branch_id)`
    """
    cli_response, response, exit_code = execute_command(convo.agent.project,
                                                        command,
                                                        timeout=timeout,
                                                        success_message=success_message,
                                                        process_name=process_name,
                                                        force=force)

    if response is None:
        logger.info(f'`{command}` exit code: {exit_code}')
        if exit_code is None:
            response = 'DONE'
        else:
            # "I ran the command and the output was... respond with 'DONE' or 'NEEDS_DEBUGGING'"
            response = convo.send_message('dev_ops/ran_command.prompt',
                {
                    'cli_response': cli_response,
                    'command': command,
                    'additional_message': additional_message,
                    'exit_code': exit_code
                })
            logger.debug(f'LLM response: {response}')

    if response != 'DONE':
        # 'NEEDS_DEBUGGING'
        print(red(f'Got incorrect CLI response:'))
        print(cli_response)
        print(red('-------------------'))

        reset_branch_id = convo.save_branch()
        while True:
            try:
                # This catch is necessary to return the correct value (cli_response) to continue development function so
                # the developer can debug the appropriate issue
                # this snippet represents the first entry point into debugging recursion because of return_cli_response
                return convo.agent.debugger.debug(convo, {'command': command, 'timeout': timeout})
            except TooDeepRecursionError as e:
                # this is only to put appropriate message in the response after TooDeepRecursionError is raised
                raise TooDeepRecursionError(cli_response) if return_cli_response else e
            except TokenLimitError as e:
                if is_root_task:
                    convo.load_branch(reset_branch_id)
                else:
                    raise e
    else:
        return { 'success': True, 'cli_response': cli_response }
