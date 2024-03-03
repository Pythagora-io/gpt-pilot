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
                "description": "A file that should be created or updated.",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the file that will be created (if it doesn't exist) or updated (if it already exists)."
                    },
                    "path": {
                        "type": "string",
                        "description": "Full path of the file with the file name."
                    },
                    "code_change_description": {
                        "type": "string",
                        "description": "Empty string"
                    }
                },
                "required": ["name", "path", "code_change_description"]
            }
        },
        "required": ["type", "save_file"]
    }


def step_human_intervention_definition():
    return {
        "type": "object",
        "properties": {
            "type": {
                "const": "human_intervention",
                "description": 'Development step that will be executed by a human. You should avoid using this step if possible, task does NOT need to have "human_intervention" step.'
            },
            "human_intervention_description": {
                "type": "string",
                "description": "Very clear description of step where human intervention is needed."
            }
        },
        "required": ["type", "human_intervention_description"]
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
                    'template': {
                        'type': ['string', 'null'],
                        'description': 'One of the available project templates.',
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

ALTERNATIVE_SOLUTIONS = {
    'definitions': [
        {
            'name': 'get_alternative_solutions_to_issue',
            'description': 'Gets alternative solutions to the recurring issue that was labeled as loop by the user.',
            'parameters': {
                'type': 'object',
                "properties": {
                    "description_of_tried_solutions": {
                        'type': 'string',
                        'description': 'A description of the solutions that were tried to solve the recurring issue that was labeled as loop by the user.',
                    },
                    "alternative_solutions": {
                        'type': 'array',
                        'description': 'List of all alternative solutions to the recurring issue that was labeled as loop by the user.',
                        'items': {
                            'type': 'string',
                            'description': 'Development step that needs to be done to complete the entire task.',
                        }
                    }
                },
                "required": ['description_of_tried_solutions', 'alternative_solutions'],
            },
        }
    ]
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
                            }
                        },
                        'required': ['description'],
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
                                step_save_file_definition(),
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

REVIEW_CHANGES = {
    'definitions': [{
        'name': 'review_diff',
        'description': 'Review a unified diff and select hunks to apply or rework.',
        'parameters': {
            "type": "object",
            "properties": {
                "hunks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {
                                "type": "integer",
                                "description": "Index of the hunk in the diff. Starts from 1."
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for applying or ignoring this hunk, or for asking for it to be reworked."
                            },
                            "decision": {
                                "type": "string",
                                "enum": ["apply", "ignore", "rework"],
                                "description": "Whether to apply this hunk (if it's a valid change with no problems), rework (a valid change but does something incorrectly), or ignore it (unwanted change)."
                            }
                        },
                        "required": ["number", "reason", "decision"],
                        "additionalProperties": False
                    },
                },
                "review_notes": {
                    "type": "string"
                }
            },
            "required": ["hunks", "review_notes"],
            "additionalProperties": False
        }
    }],
}

GET_BUG_REPORT_MISSING_DATA = {
    'definitions': [{
        'name': 'bug_report_missing_data',
        'description': 'Review bug report and identify missing data. List questions that need to be answered to proceed with the bug fix. If no additional questions are needed missing_data should be an empty array.',
        'parameters': {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Reasoning for asking these questions or for not asking any questions."
                },
                "missing_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["general", "frontend", "backend", "database", "devops", "other"],
                                "description": "Category of the question."
                            },
                            "question": {
                                "type": "string",
                                "description": "Very clear question that needs to be answered to have good bug report.",
                            },
                        },
                        "required": ["category", "question"],
                        "additionalProperties": False
                    },
                }
            },
            "required": ["reasoning", "missing_data"],
            "additionalProperties": False
        }
    }],
}
