import subprocess
import os
import signal
import threading
import queue
import time

from termcolor import colored
from database.database import get_command_run_from_hash_id, save_command_run
from const.function_calls import DEBUG_STEPS_BREAKDOWN

from utils.questionary import styled_text
from const.code_execution import MAX_COMMAND_DEBUG_TRIES

def enqueue_output(out, q):
    for line in iter(out.readline, ''):
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


def execute_command(project, command, timeout=5000):
    # check if we already have the command run saved
    timeout = max(timeout, 2000)
    print(colored(f'Can i execute the command: `{command}` with {timeout}ms timeout?', 'white', attrs=['bold']))
    project.command_runs_count += 1
    command_run = get_command_run_from_hash_id(project, command)
    if command_run is not None and project.skip_steps:
        # if we do, use it
        print(colored(f'Restoring command run response id {command_run.id}:\n```\n{command_run.cli_response}```', 'yellow'))
        return command_run.cli_response

    answer = styled_text(
        project,
        'If yes, just press ENTER and if not, please paste the output of running this command here and press ENTER'
    )

    return_value = None

    if answer != '':
        return_value = answer[-2000:]

    q_stderr = queue.Queue()
    q = queue.Queue()
    pid_container = [None]
    process = run_command(command, project.root_path, q, q_stderr, pid_container)
    output = ''
    start_time = time.time()

    while True and return_value is None:
        elapsed_time = time.time() - start_time
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
        if elapsed_time * 1000 > timeout:
            os.killpg(pid_container[0], signal.SIGKILL)
            break

        try:
            line = q.get_nowait()
        except queue.Empty:
            line = None

        if line:
            output += line
            print(colored('CLI OUTPUT:', 'green') + line, end='')

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

def build_directory_tree(path, prefix="", ignore=None, is_last=False):
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
        output += prefix + "|-- " + os.path.basename(path) + "/\n"

        # List items in the directory
        items = os.listdir(path)
        for index, item in enumerate(items):
            item_path = os.path.join(path, item)
            output += build_directory_tree(item_path, prefix + indent, ignore, index == len(items) - 1)

    else:
        # It's a file, add its name to the output
        output += prefix + "|-- " + os.path.basename(path) + "\n"

    return output

def execute_command_and_check_cli_response(command, timeout, convo):
    cli_response = execute_command(convo.agent.project, command, timeout)
    response = convo.send_message('dev_ops/ran_command.prompt',
        { 'cli_response': cli_response, 'command': command })
    return response

def run_command_until_success(command, timeout, convo):
    command_executed = False
    for i in range(MAX_COMMAND_DEBUG_TRIES):
        cli_response = execute_command(convo.agent.project, command, timeout)
        response = convo.send_message('dev_ops/ran_command.prompt',
            {'cli_response': cli_response, 'command': command})

        command_executed = response == 'DONE'
        if command_executed:
            break

        print(colored(f'Got incorrect CLI response:', 'red'))
        print(cli_response)
        print(colored('-------------------', 'red'))
        debugging_plan = convo.send_message('dev_ops/debug.prompt',
            { 'command': command, 'debugging_try_num': i },
            DEBUG_STEPS_BREAKDOWN)

        # TODO refactor to nicely get the developer agent
        convo.agent.project.developer.execute_task(
            convo,
            debugging_plan,
            {'command': command, 'timeout': timeout},
            False)

    if not command_executed:
        # TODO explain better how should the user approach debugging
        # we can copy the entire convo to clipboard so they can paste it in the playground
        convo.agent.project.ask_for_human_intervention(
            'It seems like I cannot debug this problem by myself. Can you please help me and try debugging it yourself?',
            command
        )
