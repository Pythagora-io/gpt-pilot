import json
from uuid import uuid4

from utils.telemetry import telemetry
from utils.exit import trace_code_event
from const.telemetry import LOOP_THRESHOLD


class Task:
    """
    Task data structure to store information about the current task. The task data structure is sent to telemetry.
    Currently used to trace big loops in the code.

    >>> from utils.task import Task

    To set up a new task:

    >>> task = Task()

    To set a value:

    >>> task.set('task_description', 'test')

    To increment a value:

    >>> task.inc('steps')

    To start a new task:

    >>> task.start_new_task('test', 1)

    When debugging recursion happens inside a task (see pilot/helpers/Debugger.py) we add a debugging task to the
    task data structure. To add a debugging task:

    >>> task.add_debugging_task(1, {'command': 'test'}, 'This is not working', 'Command is not working')

    To clear the task:

    >>> task.clear()

    To send the task:

    >>> task.send()

    Note: the task will be sent automatically if the number of steps exceeds the threshold
    """

    def __init__(self):
        self.initial_data = {
            'task_description': '',
            'task_number': 0,
            'steps': 0,
            'debugging': [],
        }
        self.data = self.initial_data.copy()
        self.ping_extension = True

    def set(self, key: str, value: any):
        """
        Set a value in the task data

        :param key: key to set
        :param value: value to set
        """
        self.data[key] = value

    def inc(self, key: str, value: int = 1):
        """
        Increment a value in the task data

        :param key: key to increment
        :param value: value to increment by
        """
        self.data[key] += value
        if key == 'steps' and self.data[key] == LOOP_THRESHOLD + 1:
            self.send()

    def start_new_task(self, task_description: str, i: int):
        """
        Start a new task

        :param task_description: description of the task
        :param i: task number
        """
        self.send(name='loop-end')
        self.clear()
        self.set('task_description', task_description)
        self.set('task_number', i)
        self.set('loopId', f"{uuid4()}")

    def add_debugging_task(self, recursion_layer: int = None,
                           command: dict = None,
                           user_input: str = None,
                           issue_description: str = None):
        """
        Add a debugging task to the task data structure

        :param recursion_layer: recursion layer
        :param command: command to debug
        :param user_input: user input
        :param issue_description: description of the issue
        """
        self.data['debugging'].append({
            'recursion_layer': recursion_layer,
            'command': command,
            'user_inputs': [user_input] if user_input is not None else [],
            'issue_description': issue_description,
        })

    def add_user_input_to_debugging_task(self, user_input: str):
        """
        Add user input to the last debugging task

        :param user_input: user input
        """
        if self.data.get('debugging') and len(self.data['debugging']) > 0:
            self.data['debugging'][-1]['user_inputs'].append(user_input)

    def clear(self):
        """
        Clear all the task data
        """
        self.data = self.initial_data.copy()

    def send(self, name: str = 'loop-start', force: bool = False):
        """
        Send the task data to telemetry

        :param name: name of the event
        :param force: force send the task data to telemetry
        """
        if self.data['steps'] > LOOP_THRESHOLD or force:
            full_data = telemetry.data.copy()
            full_data['task_with_loop'] = self.data.copy()
            trace_code_event(name=name, data=full_data)
            if self.ping_extension and not force:
                print(json.dumps({
                    'pathId': telemetry.telemetry_id,
                    'data': full_data,
                }), type='loopTrigger')
                # TODO: see if we want to ping the extension multiple times
                self.ping_extension = False

    def exit(self):
        """
        Send the task data to telemetry and exit the process
        """
        self.send(name='loop-end')
