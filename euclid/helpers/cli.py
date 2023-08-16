import subprocess
import os
import signal
import threading
import queue
import time
import uuid

from termcolor import colored
from database.database import get_command_run_from_hash_id, save_command_run
from const.function_calls import DEBUG_STEPS_BREAKDOWN

from utils.questionary import styled_text
from const.code_execution import MAX_COMMAND_DEBUG_TRIES, MIN_COMMAND_RUN_TIME, MAX_COMMAND_RUN_TIME

interrupted = False

def enqueue_output(out, q):
    for line in iter(out.readline, ''):
        if interrupted:  # Check if the flag is set
            break
        q.put(line)
    out.close()

def run_command(command, root_path, q_stdout, q_stderr, pid_container):
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,
        cwd=root_path
    )
    pid_container[0] = process.pid
    t_stdout = threading.Thread(target=enqueue_output, args=(process.stdout, q_stdout))
    t_stderr = threading.Thread(target=enqueue_output, args=(process.stderr, q_stderr))
    t_stdout.daemon = True
    t_stderr.daemon = True
    t_stdout.start()
    t_stderr.start()
    return process


def execute_command(project, command, timeout=None, force=False):
    if timeout is not None:
        if timeout < 1000:
            timeout *= 1000
        timeout = min(max(timeout, MIN_COMMAND_RUN_TIME), MAX_COMMAND_RUN_TIME)

    if not force:
        print(colored(f'Can i execute the command: `') + colored(command, 'white', attrs=['bold']) + colored(f'` with {timeout}ms timeout?'))

        answer = styled_text(
            project,
            'If yes, just press ENTER'
        )

    project.command_runs_count += 1
    command_run = get_command_run_from_hash_id(project, command)
    if command_run is not None and project.skip_steps:
        # if we do, use it
        project.checkpoints['last_command_run'] = command_run
        print(colored(f'Restoring command run response id {command_run.id}:\n```\n{command_run.cli_response}```', 'yellow'))
        return command_run.cli_response

    return_value = None

    q_stderr = queue.Queue()
    q = queue.Queue()
    pid_container = [None]
    process = run_command(command, project.root_path, q, q_stderr, pid_container)
    output = ''
    start_time = time.time()
    interrupted = False

    try:
        while True and return_value is None:
            elapsed_time = time.time() - start_time
            print(colored(f'\rt: {round(elapsed_time * 1000)}ms : ', 'white', attrs=['bold']), end='', flush=True)
            # Check if process has finished
            if process.poll() is not None:
                # Get remaining lines from the queue
                time.sleep(0.1) # TODO this shouldn't be used
                while not q.empty():
                    output_line = q.get_nowait()
                    if output_line not in output:
                        print(colored('CLI OUTPUT:', 'green') + output_line, end='')
                        output += output_line
                break

            # If timeout is reached, kill the process
            if timeout is not None and elapsed_time * 1000 > timeout:
                raise TimeoutError("Command exceeded the specified timeout.")
                # os.killpg(pid_container[0], signal.SIGKILL)
                # break

            try:
                line = q.get_nowait()
            except queue.Empty:
                line = None

            if line:
                output += line
                print(colored('CLI OUTPUT:', 'green') + line, end='')
    except (KeyboardInterrupt, TimeoutError) as e:
        interrupted = True
        if isinstance(e, KeyboardInterrupt):
            print("\nCTRL+C detected. Stopping command execution...")
        else:
            print("\nTimeout detected. Stopping command execution...")

        os.killpg(pid_container[0], signal.SIGKILL)  # Kill the process group

    stderr_output = ''
    while not q_stderr.empty():
        stderr_output += q_stderr.get_nowait()

    if return_value is None:
        return_value = ''
        if stderr_output != '':
            return_value = 'stderr:\n```\n' + stderr_output[-2000:] + '\n```\n'
        return_value += 'stdout:\n```\n' + output[-2000:] + '\n```'

    command_run = save_command_run(project, command, return_value)

    return return_value

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
    cli_response = execute_command(convo.agent.project, command, timeout)
    response = convo.send_message('dev_ops/ran_command.prompt',
        { 'cli_response': cli_response, 'command': command })
    return cli_response, response

def run_command_until_success(command, timeout, convo, additional_message=None, force=False):
    cli_response = execute_command(convo.agent.project, command, timeout, force)
    response = convo.send_message('dev_ops/ran_command.prompt',
        {'cli_response': cli_response, 'command': command, 'additional_message': additional_message})

    if response != 'DONE':
        print(colored(f'Got incorrect CLI response:', 'red'))
        print(cli_response)
        print(colored('-------------------', 'red'))

        debug(convo, {'command': command, 'timeout': timeout})



def debug(convo, command=None, user_input=None, issue_description=None):
    function_uuid = str(uuid.uuid4())
    convo.save_branch(function_uuid)
    success = False

    for i in range(MAX_COMMAND_DEBUG_TRIES):
        if success:
            break

        convo.load_branch(function_uuid)

        debugging_plan = convo.send_message('dev_ops/debug.prompt',
            { 'command': command['command'] if command is not None else None, 'user_input': user_input, 'issue_description': issue_description },
            DEBUG_STEPS_BREAKDOWN)

        # TODO refactor to nicely get the developer agent
        success = convo.agent.project.developer.execute_task(
            convo,
            debugging_plan,
            command,
            False,
            False)


    if not success:
        # TODO explain better how should the user approach debugging
        # we can copy the entire convo to clipboard so they can paste it in the playground
        user_input = convo.agent.project.ask_for_human_intervention(
            'It seems like I cannot debug this problem by myself. Can you please help me and try debugging it yourself?' if user_input is None else f'Can you check this again:\n{issue_description}?',
            command
        )

        if user_input == 'continue':
            success = True

    return success
