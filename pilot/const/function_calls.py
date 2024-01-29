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
                    "description": f"List of {name_plural}.",
                    "items": {
                        "type": "string",
                        "description": f"{name_singular}"
                    },
                },
            },
            "required": [return_var_name],
        },
    }


def dev_step_type_description():
    return "Type of the development step that needs to be done to complete the entire task."


def step_command_definition(extended=False):
    # Base properties and required fields
    properties = {
        "type": {
            "const": "command",
            "description": dev_step_type_description()
        },
        "command": command_definition(),
    }
    required = ["type", "command"]

    # Extended properties
    if extended:
        properties.update({
            "need_to_see_output": {
                "type": "boolean",
                "description": "Set to `true` if the definition of subsequent steps may need to change after you see the output of a successful execution of this step. For example, if the purpose of a command is to check the status of a service or contents of a file before deciding how to proceed then this flag should be set to `true`. If subsequent steps can be executed as long as this step is successful, then this flag does not need to be set."
            },
            "check_if_fixed": {
                "type": "boolean",
                "description": "Flag that indicates if the original command that triggered the error that's being debugged should be tried after this step to check if the error is fixed. If you think that the original command `delete node_modules/ && delete package-lock.json` will pass after this step, then this flag should be set to TRUE and if you think that the original command will still fail after this step, then this flag should be set to `false`."
            }
        })
        # Update required fields when extended
        required.extend(["need_to_see_output", "check_if_fixed"])

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def step_save_file_definition():
    return {
        "type": "object",
        "properties": {
            "type": {
                "const": "save_file",
                "description": dev_step_type_description()
            },
            "save_file": {
                "type": "object",
                "description": "A file that needs to be created or file that needs to be completely replaced. This should be used for new files.",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the file that needs to be created or replaced."
                    },
                    "path": {
                        "type": "string",
                        "description": "Full path of the file (with the file name) that needs to be created or replaced."
                    },
                    "content": {
                        "type": "string",
                        "description": "Full content of the file that needs to be implemented. Remember, you MUST NOT omit any of the content that should go into this file."
                    }
                },
                "required": ["name", "path", "content"]
            }
        },
        "required": ["type", "save_file"]
    }


def step_modify_file_definition():
    return {
        "type": "object",
        "properties": {
            "type": {
                "const": "modify_file",
                "description": dev_step_type_description()
            },
            "modify_file": {
                "type": "object",
                "description": "A file that should be modified. This should only be used for existing files.",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the existing file that needs to be updated."
                    },
                    "path": {
                        "type": "string",
                        "description": "Full path of the file with the file name that needs to be updated."
                    },
                    "code_change_description": {
                        "type": "string",
                        "description": "Detailed description, with code snippets and any relevant context/explanation, of the changes that the developer should do."
                    }
                },
                "required": ["name", "path", "code_change_description"]
            }
        },
        "required": ["type", "modify_file"]
    }


def step_human_intervention_definition():
    return {
        "type": "object",
        "properties": {
            "type": {
                "const": "human_intervention",
                "description": dev_step_type_description()
            },
            "human_intervention_description": {
                "type": "string",
                "description": "Description of step where human intervention is needed."
            }
        },
        "required": ["type", "human_intervention_description"]
    }


def step_code_change_definition():
    return {
        "type": "object",
        "properties": {
            "type": {
                "const": "code_change",
                "description": dev_step_type_description()
            },
            "code_change_description": {
                "type": "string",
                "description": "Description of a step in debugging this issue when there are code changes required. This should thoroughly describe what needs to be done to implement the code change for a single file - it cannot include changes for multiple files."
            }
        },
        "required": ["type", "code_change_description"]
    }


def command_definition(description_command='A single command that needs to be executed.',
                       description_timeout=
                       'Timeout in milliseconds that represent the approximate time this command takes to finish. '
                       'If you need to run a command that doesnt\'t finish by itself (eg. a command to run an app), '
                       'set the timeout to to a value long enough to determine that it has started successfully and provide a command_id. '
                       'If you need to create a directory that doesn\'t exist and is not the root project directory, '
                       'always create it by running a command `mkdir`'):
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
            },
            'success_message': {
                'type': 'string',
                'description': 'A message to look for in the output of the command to determine if successful or not.',
            },
            'command_id': {
                'type': 'string',
                'description': 'If the process needs to continue running after the command is executed provide '
                               'a unique command identifier which you can use to kill the process later.',
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
        {
            'name': 'process_architecture',
            'description': "Get architecture and the list of system dependencies required for the project.",
            'parameters': {
                'type': 'object',
                "properties": {
                    "architecture": {
                        "type": "string",
                        "description": "General description of the app architecture.",
                    },
                    "system_dependencies": {
                        "type": "array",
                        "description": "List of system dependencies required to build and run the app.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the system dependency, for example Node.js or Python."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "One-line description of the dependency.",
                                },
                                "test": {
                                    "type": "string",
                                    "description": "Command line to test whether the dependency is available on the system.",
                                },
                                "required_locally": {
                                    "type": "boolean",
                                    "description": "Whether this dependency must be installed locally (as opposed to connecting to cloud or other server)",
                                }
                            },
                            "required": ["name", "description", "test", "required_locally"],
                        },
                    },
                    "package_dependencies": {
                        "type": "array",
                        "description": "List of framework/language-specific packages used by the app.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the package dependency, for example Express or React."
                                },
                                "description": {
                                    "type": "string",
                                    "description": "One-line description of the dependency.",
                                }
                            },
                            "required": ["name", "description"],
                        },
                    },
                },
                "required": ["architecture", "system_dependencies", "package_dependencies"],
            },
        },
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

COMMAND_TO_RUN = {
    'definitions': [
        {
            'name': 'command_to_run',
            'description': 'Command that starts the app.',
            'parameters': command_definition("Command that starts the app. If app can't be started for some reason, return command as empty string ''."),
        },
    ],
    'functions': {
        'process_commands': run_commands
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
                        'description': 'List of smaller development steps.',
                        'items': {
                            "oneOf": [
                                step_command_definition(),
                                step_save_file_definition(),
                                step_modify_file_definition(),
                                step_human_intervention_definition(),
                            ]
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
            'description': 'Returns development files that are currently implemented so that they can be analized and so that changes can be appropriatelly made.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'files': {
                        'type': 'array',
                        'description': 'List of files that need to be analyzed to implement the required changes.',
                        'items': {
                            'type': 'string',
                            'description': 'A single file name that needs to be analized to implement the reqired changes. Remember, this is a file name with path relative to the project root. For example, if a file path is `{{project_root}}/models/model.py`, this value needs to be `models/model.py`.',
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
                            'description': 'A smaller development step that needs to be done to complete the entire task.  Remember, if you need to run a command that doesn\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                            'properties': {
                                'type': {
                                    'type': 'string',
                                    'enum': ['command', 'code_change'],
                                    'description': 'Type of the development step that needs to be done to complete the entire task.',
                                },
                                'command': command_definition('Command that needs to be run to complete the current task. This should be used only if the task is of a type "command".', 'Timeout in milliseconds that represent the approximate time the command takes to finish. This should be used only if the task is of a type "command". If you need to run a command that doesn\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. Remember, this is not in seconds but in milliseconds so likely it always needs to be greater than 1000.'),
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
                        'description': 'Development task that needs to be done to implement the entire plan. It contains all details that developer who is not familiar with project needs to know to implement the task.',
                        'properties': {
                            'description': {
                                'type': 'string',
                                'description': 'Very detailed description of the development task that needs to be done to implement the entire plan.',
                            },
                            'user_review_goal': {
                                'type': 'string',
                                'description': 'User review goal that will determine if a task is done or not, but from a user perspective since it will be reviewed by a human.',
                            }
                        },
                        'required': ['description', 'user_review_goal'],
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
        'description': 'Executes a list of commands. ',
        'parameters': {
            'type': 'object',
            'properties': {
                'commands': {
                    'type': 'array',
                    'description': 'List of commands that need to be executed.  Remember, if you need to run a command that doesn\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`',
                    'items': command_definition('A single command that needs to be executed.',
                                                'Timeout in milliseconds that represent the approximate time this command takes to finish. If you need to run a command that doesn\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds.')
                }
            },
            'required': ['commands'],
        },
    }],
    'functions': {
        'execute_commands': lambda commands: commands
    }
}

GET_FILE_TO_MODIFY = {
    'definitions': [{
        'name': 'get_file_to_modify',
        'description': 'File that needs to be modified.',
        'parameters': {
            'type': 'object',
            'properties': {
                'file': {
                    'type': 'string',
                    'description': 'Path to the file that needs to be modified, relative to the project root.',
                }
            }
        }
    }],
    'functions': {
        'get_file_to_modify': lambda file: file
    }
}


GET_TEST_TYPE = {
    'definitions': [{
        'name': 'test_changes',
        'description': 'Tests the changes based on the test type.',
        'parameters': {
            'type': 'object',
            'properties': {
                'type': {
                    'type': 'string',
                    'description': 'Type of a test that needs to be run. If this is just an intermediate step in getting a task done, put `no_test` as the type and we\'ll just go onto the next task without testing.',
                    'enum': ['command_test', 'manual_test', 'no_test']
                },
                'command': command_definition('Command that needs to be run to test the changes.', 'Timeout in milliseconds that represent the approximate time this command takes to finish. If you need to run a command that doesn\'t finish by itself (eg. a command to run an app), put the timeout to 3000 milliseconds. If you need to create a directory that doesn\'t exist and is not the root project directory, always create it by running a command `mkdir`'),
                # 'automated_test_description': {
                #     'type': 'string',
                #     'description': 'Description of an automated test that needs to be run to test the changes. This should be used only if the test type is "automated_test" and it should thoroughly describe what needs to be done to implement the automated test so that when someone looks at this test can know exactly what needs to be done to implement this automated test.',
                # },
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
                'properties': {
                    'steps': {
                        'type': 'array',
                        'description': 'List of steps that need to be done to debug the problem.',
                        'items': {
                            "oneOf": [
                                step_command_definition(True),
                                step_code_change_definition(),
                                step_human_intervention_definition(),
                            ]
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

GET_MISSING_SNIPPETS = {
    'definitions': [{
        'name': 'get_missing_snippets',
        'description': 'Gets the list of snippets that are missing from the code.',
        'parameters': {
            'type': 'object',
            'properties': {
                'snippets': {
                    'type': 'array',
                    'description': 'List of snippets that are missing from the code.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'comment_label': {
                                'type': 'string',
                                'description': 'Comment label that identifies the snippet that needs to be inserted.',
                            },
                            'snippet': {
                                'type': 'string',
                                'description': 'The code from earlier in this conversation that needs to be inserted instead of the comment. **IMPORTANT** You always need to write the entire snippet, and under no circumstances should you ever leave any part of the code snippet unwritten. **IMPORTANT** Every single line of code that exists in the place where the comment lives right now should be replaced. **IMPORTANT** Do not include any code that is above or below the comment but only the code that should be in the position of the comment. **IMPORTANT** Make sure that you write the entire snippet that should be inserted in the place of the comment_label, including all control structures, error handling, and any other relevant logic that was in the original code.',
                            },
                            'file_path': {
                                'type': 'string',
                                'description': 'Path to the file where the snippet needs to be inserted.',
                            }
                        },
                        'required': ['comment_label', 'snippet', 'file_path'],
                    }
                }
            },
            'required': ['snippets'],
        },
    }],
}

GET_DOCUMENTATION_FILE = {
    'definitions': [{
        'name': 'get_documentation_file',
        'description': 'Gets the full content of requested documentation file.',
        'parameters': {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'description': 'Name of the documentation file that needs to be saved on the disk.',
                },
                'path': {
                    'type': 'string',
                    'description': 'Relative path of the documentation file with the file name that needs to be saved.',
                },
                'content': {
                    'type': 'string',
                    'description': 'Full content of the documentation file that needs to be saved on the disk.',
                },
            },
            'required': ['name', 'path', 'content'],
        },
    }],
}
