def process_user_stories(stories):
    return stories


def process_user_tasks(tasks):
    return tasks


def process_os_technologies(technologies):
    return technologies


def run_commands(commands):
    return commands


def return_files(files):
    # TODO get file
    return files


def return_array_from_prompt(name_plural, name_singular, return_var_name):
    return {
        'name': f'process_{name_plural.replace(" ", "_")}',
        'description': f"Print the list of {name_plural} that are created.",
        'parameters': {
            'type': 'object',
            "properties": {
                f"{return_var_name}": {
                    "type": "array",
                    "description": f"List of {name_plural} that are created in a list.",
                    "items": {
                        "type": "string",
                        "description": f"{name_singular}"
                    },
                },
            },
            "required": [return_var_name],
        },
    }


def command_definition(description_command=f'A single command that needs to be executed.', description_timeout=f'Timeout in milliseconds that represent the approximate time this command takes to finish. If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`'):
    return {
        'type': 'object',
        'description': 'Command that needs to be run to complete the current task. This should be used only if the task is of a type "command".',
        'properties': {
            'command': {
                'type': 'string',
                'description': description_command,
            },
            'timeout': {
                'type': 'number',
                'description': description_timeout,
            }
        },
        'required': ['command', 'timeout'],
    }


USER_STORIES = {
    'definitions': [
        return_array_from_prompt('user stories', 'user story', 'stories')
    ],
    'functions': {
        'process_user_stories': process_user_stories
    },
}

USER_TASKS = {
    'definitions': [
        return_array_from_prompt('user tasks', 'user task', 'tasks')
    ],
    'functions': {
        'process_user_tasks': process_user_tasks
    },
}

ARCHITECTURE = {
    'definitions': [
        return_array_from_prompt('technologies', 'technology', 'technologies')
    ],
    'functions': {
        'process_technologies': lambda technologies: technologies
    },
}

FILTER_OS_TECHNOLOGIES = {
    'definitions': [
        return_array_from_prompt('os specific technologies', 'os specific technology', 'technologies')
    ],
    'functions': {
        'process_os_specific_technologies': process_os_technologies
    },
}

INSTALL_TECH = {
    'definitions': [
        return_array_from_prompt('os specific technologies', 'os specific technology', 'technologies')
    ],
    'functions': {
        'process_os_specific_technologies': process_os_technologies
    },
}

COMMANDS_TO_RUN = {
    'definitions': [
        return_array_from_prompt('commands', 'command', 'commands')
    ],
    'functions': {
        'process_commands': run_commands
    },
}

DEV_TASKS_BREAKDOWN = {
    'definitions': [
        {
            'name': 'break_down_development_task',
            'description': 'Breaks down the development task into smaller steps that need to be done to implement the entire task.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "tasks": {
                        'type': 'array',
                        'description': 'List of smaller development steps that need to be done to complete the entire task.',
                        'items': {
                            'type': 'object',
                            'description': 'A smaller development step that needs to be done to complete the entire task.  Remember, if you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                            'properties': {
                                'type': {
                                    'type': 'string',
                                    'enum': ['command', 'code_change', 'human_intervention'],
                                    'description': 'Type of the development step that needs to be done to complete the entire task.',
                                },
                                'command': command_definition(f'A single command that needs to be executed.', 'Timeout in milliseconds that represent the approximate time the command takes to finish. This should be used only if the task is of a type "command". If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. Remember, this is not in seconds but in milliseconds so likely it always needs to be greater than 1000.'),
                                'code_change_description': {
                                    'type': 'string',
                                    'description': 'Description of a the development step that needs to be done. This should be used only if the task is of a type "code_change" and it should thoroughly describe what needs to be done to implement the code change for a single file - it cannot include changes for multiple files.',
                                },
                                'human_intervention_description': {
                                    'type': 'string',
                                    'description': 'Description of a task that requires a human to do.',
                                },
                            },
                            'required': ['type'],
                        }
                    }
                },
                "required": ['tasks'],
            },
        },
    ],
    'functions': {
        'break_down_development_task': lambda tasks: tasks
    },
}

IMPLEMENT_TASK = {
    'definitions': [
        {
            'name': 'parse_development_task',
            'description': 'Breaks down the development task into smaller steps that need to be done to implement the entire task.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "tasks": {
                        'type': 'array',
                        'description': 'List of smaller development steps that need to be done to complete the entire task.',
                        'items': {
                            'type': 'object',
                            'description': 'A smaller development step that needs to be done to complete the entire task.  Remember, if you need to run a command that doesnt\'t finish by itself (eg. a command to run an  If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                            'properties': {
                                'type': {
                                    'type': 'string',
                                    'enum': ['command', 'code_change', 'human_intervention'],
                                    'description': 'Type of the development step that needs to be done to complete the entire task.',
                                },
                                'command': command_definition(),
                                'code_change': {
                                    'type': 'object',
                                    'description': 'A code change that needs to be implemented. This should be used only if the task is of a type "code_change".',
                                    'properties': {
                                        'name': {
                                            'type': 'string',
                                            'description': 'Name of the file that needs to be implemented.',
                                        },
                                        'path': {
                                            'type': 'string',
                                            'description': 'Full path of the file with the file name that needs to be implemented.',
                                        },
                                        'content': {
                                            'type': 'string',
                                            'description': 'Full content of the file that needs to be implemented.',
                                        },
                                    },
                                    'required': ['name', 'path', 'content'],
                                },
                                'human_intervention_description': {
                                    'type': 'string',
                                    'description': 'Description of a step in debugging this issue when there is a human intervention needed. This should be used only if the task is of a type "human_intervention".',
                                },
                            },
                            'required': ['type'],
                        }
                    }
                },
                "required": ['tasks'],
            },
        },
    ],
    'functions': {
        'parse_development_task': lambda tasks: tasks
    },
}

DEV_STEPS = {
    'definitions': [
        {
            'name': 'break_down_development_task',
            'description': 'Breaks down the development task into smaller steps that need to be done to implement the entire task.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "tasks": {
                        'type': 'array',
                        'description': 'List of development steps that need to be done to complete the entire task.',
                        'items': {
                            'type': 'object',
                            'description': 'Development step that needs to be done to complete the entire task.',
                            'properties': {
                                'type': {
                                    'type': 'string',
                                    'description': 'Type of the development step that needs to be done to complete the entire task - it can be "command" or "code_change".',
                                },
                                'description': {
                                    'type': 'string',
                                    'description': 'Description of the development step that needs to be done.',
                                },
                            },
                            'required': ['type', 'description'],
                        }
                    }
                },
                "required": ['tasks'],
            },
        },
        {
            'name': 'run_commands',
            'description': 'Run all commands in the given list. Each command needs to be a single command that can be executed.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "commands": {
                        'type': 'array',
                        'description': 'List of commands that need to be run to complete the currrent task. Each command cannot be anything other than a single CLI command that can be independetly run.',
                        'items': {
                            'type': 'string',
                            'description': 'A single command that needs to be run to complete the current task.',
                        }
                    }
                },
                "required": ['commands'],
            },
        },
        {
            'name': 'process_code_changes',
            'description': 'Implements all the code changes outlined in the description.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "code_change_description": {
                        'type': 'string',
                        'description': 'A detailed description of what needs to be done to implement all the code changes from the task.',
                    }
                },
                "required": ['code_change_description'],
            },
        },
        {
            'name': 'get_files',
            'description': f'Returns development files that are currently implemented so that they can be analized and so that changes can be appropriatelly made.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'files': {
                        'type': 'array',
                        'description': f'List of files that need to be analized to implement the reqired changes.',
                        'items': {
                            'type': 'string',
                            'description': f'A single file name that needs to be analized to implement the reqired changes. Remember, this is a file name with path relative to the project root. For example, if a file path is `{{project_root}}/models/model.py`, this value needs to be `models/model.py`.',
                        }
                    }
                },
                'required': ['files'],
            },
        }
    ],
    'functions': {
        'break_down_development_task': lambda tasks: (tasks, 'more_tasks'),
        'run_commands': lambda commands: (commands, 'run_commands'),
        'process_code_changes': lambda code_change_description: (code_change_description, 'code_changes'),
        'get_files': return_files
    },
}

CODE_CHANGES = {
    'definitions': [
        {
            'name': 'break_down_development_task',
            'description': 'Implements all the smaller tasks that need to be done to complete the entire development task.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "tasks": {
                        'type': 'array',
                        'description': 'List of smaller development steps that need to be done to complete the entire task.',
                        'items': {
                            'type': 'object',
                            'description': 'A smaller development step that needs to be done to complete the entire task.  Remember, if you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                            'properties': {
                                'type': {
                                    'type': 'string',
                                    'enum': ['command', 'code_change'],
                                    'description': 'Type of the development step that needs to be done to complete the entire task.',
                                },
                                'command': command_definition('Command that needs to be run to complete the current task. This should be used only if the task is of a type "command".', 'Timeout in milliseconds that represent the approximate time the command takes to finish. This should be used only if the task is of a type "command". If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. Remember, this is not in seconds but in milliseconds so likely it always needs to be greater than 1000.'),
                                'code_change_description': {
                                    'type': 'string',
                                    'description': 'Description of a the development step that needs to be done. This should be used only if the task is of a type "code_change" and it should thoroughly describe what needs to be done to implement the code change.',
                                },
                            },
                            'required': ['type'],
                        }
                    }
                },
                "required": ['tasks'],
            },
        }
    ],
    'functions': {
        'break_down_development_task': lambda tasks: tasks,
    },
}

DEVELOPMENT_PLAN = {
    'definitions': [{
        'name': 'implement_development_plan',
        'description': 'Implements the development plan.',
        'parameters': {
            'type': 'object',
            "properties": {
                "plan": {
                    "type": "array",
                    "description": 'List of development tasks that need to be done to implement the entire plan.',
                    "items": {
                        "type": "object",
                        'description': 'Development task that needs to be done to implement the entire plan.',
                        'properties': {
                            'description': {
                                'type': 'string',
                                'description': 'Description of the development task that needs to be done to implement the entire plan.',
                            },
                            'programmatic_goal': {
                                'type': 'string',
                                'description': 'programmatic goal that will determine if a task can be marked as done from a programmatic perspective (this will result in an automated test that is run before the task is sent to you for a review)',
                            },
                            'user_review_goal': {
                                'type': 'string',
                                'description': 'user-review goal that will determine if a task is done or not but from a user perspective since it will be reviewed by a human',
                            }
                        },
                        'required': ['task_description', 'programmatic_goal', 'user_review_goal'],
                    },
                },
            },
            "required": ['plan'],
        },
    }],
    'functions': {
        'implement_development_plan': lambda plan: plan
    },
}

EXECUTE_COMMANDS = {
    'definitions': [{
        'name': 'execute_commands',
        'description': f'Executes a list of commands. ',
        'parameters': {
            'type': 'object',
            'properties': {
                'commands': {
                    'type': 'array',
                    'description': f'List of commands that need to be executed.  Remember, if you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                    'items': command_definition(f'A single command that needs to be executed.', f'Timeout in milliseconds that represent the approximate time this command takes to finish. If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds.')
                }
            },
            'required': ['commands'],
        },
    }],
    'functions': {
        'execute_commands': lambda commands: commands
    }
}

GET_FILES = {
    'definitions': [{
        'name': 'get_files',
        'description': f'Returns development files that are currently implemented so that they can be analized and so that changes can be appropriatelly made.',
        'parameters': {
            'type': 'object',
            'properties': {
                'files': {
                    'type': 'array',
                    'description': f'List of files that need to be analized to implement the reqired changes. Any file name in this array MUST be from the directory tree listed in the previous message.',
                    'items': {
                        'type': 'string',
                        'description': f'A single file name that needs to be analized to implement the reqired changes. Remember, this is a file name with path relative to the project root. For example, if a file path is `{{project_root}}/models/model.py`, this value needs to be `models/model.py`. This file name MUST be listed in the directory from the previous message.',
                    }
                }
            },
            'required': ['files'],
        },
    }],
    'functions': {
        'get_files': lambda files: files
    }
}

IMPLEMENT_CHANGES = {
    'definitions': [{
        'name': 'save_files',
        'description': 'Iterates over the files passed to this function and saves them on the disk.',
        'parameters': {
            'type': 'object',
            'properties': {
                'files': {
                    'type': 'array',
                    'description': 'List of files that need to be saved.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {
                                'type': 'string',
                                'description': 'Name of the file that needs to be saved on the disk.',
                            },
                            'path': {
                                'type': 'string',
                                'description': 'Path of the file that needs to be saved on the disk.',
                            },
                            'content': {
                                'type': 'string',
                                'description': 'Full content of the file that needs to be saved on the disk.',
                            },
                            'description': {
                                'type': 'string',
                                'description': 'Description of the file that needs to be saved on the disk. This description doesn\'t need to explain what is being done currently in this task but rather what is the idea behind this file - what do we want to put in this file in the future. Write the description ONLY if this is the first time this file is being saved. If this file already exists on the disk, leave this field empty.',
                            },
                        },
                        'required': ['name', 'path', 'content'],
                    }
                }
            },
            'required': ['files'],
        },
    }],
    'functions': {
        'save_files': lambda files: files
    },
    'to_message': lambda files: [
        f'File `{file["name"]}` saved to the disk and currently looks like this:\n```\n{file["content"]}\n```' for file
        in files]
}

GET_TEST_TYPE = {
    'definitions': [{
        'name': 'test_changes',
        'description': f'Tests the changes based on the test type.',
        'parameters': {
            'type': 'object',
            'properties': {
                'type': {
                    'type': 'string',
                    'description': f'Type of a test that needs to be run. If this is just an intermediate step in getting a task done, put `no_test` as the type and we\'ll just go onto the next task without testing.',
                    'enum': ['automated_test', 'command_test', 'manual_test', 'no_test']
                },
                'command': command_definition('Command that needs to be run to test the changes.', 'Timeout in milliseconds that represent the approximate time this command takes to finish. If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`'),
                'automated_test_description': {
                    'type': 'string',
                    'description': 'Description of an automated test that needs to be run to test the changes. This should be used only if the test type is "automated_test" and it should thoroughly describe what needs to be done to implement the automated test so that when someone looks at this test can know exactly what needs to be done to implement this automated test.',
                },
                'manual_test_description': {
                    'type': 'string',
                    'description': 'Description of a manual test that needs to be run to test the changes. This should be used only if the test type is "manual_test".',
                }
            },
            'required': ['type'],
        },
    }],
    'functions': {
        'test_changes': lambda type, command=None, automated_test_description=None, manual_test_description=None: (
            type, command, automated_test_description, manual_test_description)
    }
}

DEBUG_STEPS_BREAKDOWN = {
    'definitions': [
        {
            'name': 'start_debugging',
            'description': 'Starts the debugging process based on the list of steps that need to be done to debug the problem.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "steps": {
                        'type': 'array',
                        'description': 'List of steps that need to be done to debug the problem.',
                        'items': {
                            'type': 'object',
                            'description': 'A single step that needs to be done to get closer to debugging this issue.  Remember, if you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                            'properties': {
                                'type': {
                                    'type': 'string',
                                    'enum': ['command', 'code_change', 'human_intervention'],
                                    'description': 'Type of the step that needs to be done to debug this issue.',
                                },
                                'command': command_definition('Command that needs to be run to debug this issue.', 'Timeout in milliseconds that represent the approximate time this command takes to finish. If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds.'),
                                'code_change_description': {
                                    'type': 'string',
                                    'description': 'Description of a step in debugging this issue when there are code changes required. This should be used only if the task is of a type "code_change" and it should thoroughly describe what needs to be done to implement the code change for a single file - it cannot include changes for multiple files.',
                                },
                                'human_intervention_description': {
                                    'type': 'string',
                                    'description': 'Description of a step in debugging this issue when there is a human intervention needed. This should be used only if the task is of a type "human_intervention".',
                                },
                                "check_if_fixed": {
                                    'type': 'boolean',
                                    'description': 'Flag that indicates if the original command that triggered the error that\'s being debugged should be tried after this step to check if the error is fixed. If you think that the original command `delete node_modules/ && delete package-lock.json` will pass after this step, then this flag should be set to TRUE and if you think that the original command will still fail after this step, then this flag should be set to FALSE.',
                                }
                            },
                            'required': ['type', 'check_if_fixed'],
                        }
                    }
                },
                "required": ['steps'],
            },
        },
    ],
    'functions': {
        'start_debugging': lambda steps: steps
    },
}
