import re


def print_task_progress(index, num_of_tasks, description, task_source, status, source_index=1):
    """
    Print task progress in extension.

    :param index: Index of the task.
    :param num_of_tasks: Number of tasks.
    :param description: Description of the task.
    :param task_source: Source of the task, one of: 'app', 'feature', 'debugger', 'troubleshooting', 'review'.
    :param status: Status of the task, can be 'in_progress' or 'done'.
    :param source_index: Index of the source.

    :return: None
    """
    print({'task': {
        'index': index,
        'num_of_tasks': num_of_tasks,
        'description': description,
        'source': task_source,
        'status': status,
        'source_index': source_index,
    }}, type='progress')


def print_step_progress(index, num_of_steps, step, task_source):
    """
    Print step progress in extension.

    :param index: Index of the step.
    :param num_of_steps: Number of steps.
    :param step: Name of the step.
    :param task_source: Source of the task, one of: 'app', 'feature', 'debugger', 'troubleshooting', 'review'.

    :return: None
    """
    print({'step': {
        'index': index,
        'num_of_steps': num_of_steps,
        'step': step,
        'source': task_source,
    }}, type='progress')


def remove_ansi_codes(s: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    # Check if the input is a string
    if isinstance(s, str):
        return ansi_escape.sub('', s)
    else:
        # If the input is not a string, return the input as is
        return s
