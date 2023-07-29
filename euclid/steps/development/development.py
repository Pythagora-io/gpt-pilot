import json
from termcolor import colored

from utils.utils import execute_step, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user, execute_chat_prompt
from const.function_calls import FILTER_OS_TECHNOLOGIES, COMMANDS_TO_RUN
from const.code_execution import MAX_COMMAND_DEBUG_TRIES
from utils.utils import get_os_info
from helpers.cli import execute_command

def environment_setup():
    # env_setup/specs.prompt
    # loop through returned array
        # install_next_technology.prompt
            # cli_response.prompt
            # unsuccessful_installation.prompt

            # OR
            execute_command();

def implement_task(task):
    # development/task/breakdown.prompt
    # loop through returned array
        # development/task/step/specs.prompt
    pass

def execute_command_and_check_cli_response(command, timeout, previous_messages, current_step):
    cli_response = execute_command(command, timeout)
    response, messages = execute_chat_prompt('dev_ops/ran_command.prompt',
        { 'cli_response': cli_response, 'command': command }, current_step, previous_messages)
    return response, messages

def run_command_until_success(command, timeout, previous_messages, current_step):
    command_executed = False
    for _ in range(MAX_COMMAND_DEBUG_TRIES):
        cli_response = execute_command(command, timeout)
        response, previous_messages = execute_chat_prompt('dev_ops/ran_command.prompt',
            {'cli_response': cli_response, 'command': command}, current_step, previous_messages)
        
        command_executed = response == 'DONE'
        if command_executed:
            break

        command = response

    if not command_executed:
        # TODO ask user to debug and press enter to continue
        pass

def set_up_environment(technologies, args):
    current_step = 'environment_setup'
    role = find_role_from_step(current_step)

    steps = get_progress_steps(args['app_id'], current_step)
    if steps and not execute_step(args['step'], current_step):
        first_step = steps[0]
        data = json.loads(first_step['data'])

        app_data = data.get('app_data')
        if app_data is not None:
            args.update(app_data)

        message = f"Tech stask breakdown already done for this app_id: {args['app_id']}. Moving to next step..."
        print(colored(message, "green"))
        logger.info(message)
        return data.get('technologies'), data.get('messages')
    
    # ENVIRONMENT SETUP
    print(colored(f"Setting up the environment...\n", "green"))
    logger.info(f"Setting up the environment...")

    # TODO: remove this once the database is set up properly
    # previous_messages[2]['content'] = '\n'.join(previous_messages[2]['content'])
    # TODO END

    os_info = get_os_info()
    os_specific_techologies, previous_messages = execute_chat_prompt('development/env_setup/specs.prompt',
            { "os_info": os_info, "technologies": technologies }, current_step, function_calls=FILTER_OS_TECHNOLOGIES)

    for technology in os_specific_techologies:
        llm_response, previous_messages = execute_chat_prompt('development/env_setup/install_next_technology.prompt',
            { 'technology': technology}, current_step, previous_messages, function_calls={
                'definitions': [{
                    'name': 'execute_command',
                    'description': f'Executes a command that should check if {technology} is installed on the machine. ',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'command': {
                                'type': 'string',
                                'description': f'Command that needs to be executed to check if {technology} is installed on the machine.',
                            },
                            'timeout': {
                                'type': 'number',
                                'description': f'Timeout in seconds for the approcimate time this command takes to finish.',
                            }
                        },
                        'required': ['command', 'timeout'],
                    },
                }],
                'functions': {
                    'execute_command': execute_command_and_check_cli_response
                },
                'send_messages_and_step': True
            })
        
        if not llm_response == 'DONE':
            installation_commands, previous_messages = execute_chat_prompt('development/env_setup/unsuccessful_installation.prompt',
                { 'technology': technology }, current_step, previous_messages, function_calls={
                'definitions': [{
                    'name': 'execute_commands',
                    'description': f'Executes a list of commands that should install the {technology} on the machine. ',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'commands': {
                                 'type': 'array',
                                 'description': f'List of commands that need to be executed to install {technology} on the machine.',
                                 'items': {
                                    'type': 'object',
                                    'properties': {
                                         'command': {
                                            'type': 'string',
                                            'description': f'Command that needs to be executed as a step to install {technology} on the machine.',
                                        },
                                        'timeout': {
                                            'type': 'number',
                                            'description': f'Timeout in seconds for the approcimate time this command takes to finish.',
                                        }
                                    }
                                }
                            }
                        },
                        'required': ['commands'],
                    },
                }],
                'functions': {
                    'execute_commands': lambda commands: (commands, None)
                }
            })
            if installation_commands is not None:
                for cmd in installation_commands:
                    run_command_until_success(cmd['command'], cmd['timeout'], previous_messages, current_step)
        



    logger.info('The entire tech stack neede is installed and ready to be used.')

    save_progress(args['app_id'], current_step, {
        "os_specific_techologies": os_specific_techologies, "newly_installed_technologies": [], "app_data": generate_app_data(args)
    })

    # ENVIRONMENT SETUP END

def start_development(user_stories, user_tasks, technologies_to_use, args):
    # break down the development plan

    # TODO REMOVE THIS
    technologies_to_use = technologies_to_use.split('\n')
    # TODO END

    set_up_environment(technologies_to_use, args);
    pass