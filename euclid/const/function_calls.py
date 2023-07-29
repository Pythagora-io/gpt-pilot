from utils.llm import parse_llm_output

def process_user_stories(stories):
    return stories, None

def process_user_tasks(tasks):
    return tasks, None

def process_os_technologies(technologies):
    return technologies, None

def run_commands(commands):
    return commands, None

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

RUN_COMMAND = {
    'definitions': [

    ],
    'functions': {
        'run_command': parse_llm_output
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