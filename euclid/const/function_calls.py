def process_user_stories(stories):
    return stories

def process_user_tasks(tasks):
    return tasks

def process_os_technologies(technologies):
    return technologies

def run_commands(commands):
    return commands

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
                            'task_description': {
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
                        'required': ['command', 'timeout'],
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