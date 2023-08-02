from termcolor import colored
from helpers.AgentConvo import AgentConvo

from utils.utils import execute_step, find_role_from_step, generate_app_data, step_already_finished
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from const.function_calls import FILTER_OS_TECHNOLOGIES, DEVELOPMENT_PLAN
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


def execute_command_and_check_cli_response(command, timeout, convo):
    cli_response = execute_command(command, timeout)
    response = convo.send_message('dev_ops/ran_command.prompt',
                                  {'cli_response': cli_response, 'command': command})
    return response


def run_command_until_success(command, timeout, convo):
    command_executed = False
    for _ in range(MAX_COMMAND_DEBUG_TRIES):
        cli_response = execute_command(command, timeout)
        response = convo.send_message('dev_ops/ran_command.prompt',
                                      {'cli_response': cli_response, 'command': command})

        command_executed = response == 'DONE'
        if command_executed:
            break

        command = response

    if not command_executed:
        # TODO ask user to debug and press enter to continue
        pass


def set_up_environment(technologies, args):
    current_step = 'environment_setup'
    convo_os_specific_tech = AgentConvo(current_step)

    # If this app_id already did this step, just get all data from DB and don't ask user again
    step = get_progress_steps(args['app_id'], current_step)
    if step and not execute_step(args['step'], current_step):
        step_already_finished(args, step)
        return

    # ENVIRONMENT SETUP
    print(colored(f"Setting up the environment...\n", "green"))
    logger.info(f"Setting up the environment...")

    # TODO: remove this once the database is set up properly
    # previous_messages[2]['content'] = '\n'.join(previous_messages[2]['content'])
    # TODO END

    os_info = get_os_info()
    os_specific_techologies = convo_os_specific_tech.send_message('development/env_setup/specs.prompt',
                                                                  {"os_info": os_info, "technologies": technologies},
                                                                  FILTER_OS_TECHNOLOGIES)

    for technology in os_specific_techologies:
        llm_response = convo_os_specific_tech.send_message('development/env_setup/install_next_technology.prompt',
                                                           {'technology': technology}, {
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
                                                               'send_convo': True
                                                           })

        if not llm_response == 'DONE':
            installation_commands = convo_os_specific_tech.send_message(
                'development/env_setup/unsuccessful_installation.prompt',
                {'technology': technology}, {
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
                        'execute_commands': lambda commands: commands
                    }
                })
            if installation_commands is not None:
                for cmd in installation_commands:
                    run_command_until_success(cmd['command'], cmd['timeout'], convo_os_specific_tech)

    logger.info('The entire tech stack neede is installed and ready to be used.')

    save_progress(args['app_id'], current_step, {
        "os_specific_techologies": os_specific_techologies, "newly_installed_technologies": [],
        "app_data": generate_app_data(args)
    })
    # ENVIRONMENT SETUP END


def create_development_plan(high_level_summary, user_stories, user_tasks, technologies_to_use, args):
    current_step = 'development_planning'
    convo_development_plan = AgentConvo(current_step)

    # If this app_id already did this step, just get all data from DB and don't ask user again
    step = get_progress_steps(args['app_id'], current_step)
    if step and not execute_step(args['step'], current_step):
        step_already_finished(args, step)
        return step['development_plan']

    # DEVELOPMENT PLANNING
    print(colored(f"Starting to create the action plan for development...\n", "green"))
    logger.info(f"Starting to create the action plan for development...")

    # TODO add clarifications
    development_plan = convo_development_plan.send_message('development/plan.prompt',
                                                           {
                                                               "app_summary": high_level_summary,
                                                               "clarification": [],
                                                               "user_stories": user_stories,
                                                               "user_tasks": user_tasks,
                                                               "technologies": technologies_to_use
                                                           }, DEVELOPMENT_PLAN)

    logger.info('Plan for development is created.')

    save_progress(args['app_id'], current_step, {
        "development_plan": development_plan,
        "app_data": generate_app_data(args)
    })

    return development_plan


def start_development(user_stories, user_tasks, technologies_to_use, args):
    pass
