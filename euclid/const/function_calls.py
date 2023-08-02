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
                            'description': f'A single file name that needs to be analized to implement the reqired changes.',
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
                        'description': f'List of commands that need to be executed.',
                        'items': {
                        'type': 'object',
                        'properties': {
                                'command': {
                                'type': 'string',
                                'description': f'A single command that needs to be executed.',
                            },
                            'timeout': {
                                'type': 'number',
                                'description': f'Timeout in seconds that represent the approximate time this command takes to finish.',
                            }
                        }
                    }
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
                    'description': f'List of files that need to be analized to implement the reqired changes.',
                    'items': {
                        'type': 'string',
                        'description': f'A single file name that needs to be analized to implement the reqired changes.',
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
        'description': f'Iterates over the files passed to this function and saves them on the disk.',
        'parameters': {
            'type': 'object',
            'properties': {
                'files': {
                    'type': 'array',
                    'description': f'List of files that need to be analized to implement the reqired changes.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {
                                'type': 'string',
                                'description': f'Name of the file that needs to be saved on the disk.',
                            },
                            'content': {
                                'type': 'string',
                                'description': f'Full content of the file that needs to be saved on the disk.',
                            }
                        }
                    }
                }
            },
            'required': ['files'],
        },
    }],
    'functions': {
        'save_files': lambda files: files
    }
}