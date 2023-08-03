import json
from termcolor import colored
from utils.utils import step_already_finished
from helpers.agents.CodeMonkey import CodeMonkey
from logger.logger import logger
from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo
from utils.utils import execute_step, array_of_objects_to_string, generate_app_data
from helpers.cli import build_directory_tree, run_command_until_success, execute_command_and_check_cli_response
from const.function_calls import FILTER_OS_TECHNOLOGIES, DEVELOPMENT_PLAN, EXECUTE_COMMANDS, DEV_STEPS, GET_TEST_TYPE, DEV_TASKS_BREAKDOWN
from database.database import save_progress, get_progress_steps
from utils.utils import get_os_info
from helpers.cli import execute_command

class Developer(Agent):
    def __init__(self, project):
        super().__init__('full_stack_developer', project)

    def start_coding(self):
        self.project.current_step = 'coding'

        # DEVELOPMENT
        print(colored(f"Ok, great, now, let's start with the actual development...\n", "green"))
        logger.info(f"Starting to create the actual code...")

        for i, dev_task in enumerate(self.project.development_plan):
            self.implement_task(self.project.development_plan, i)

        # DEVELOPMENT END

        logger.info('The app is DONE!!! Yay...you can use it now.')

    def implement_task(self, sibling_tasks, current_task_index, parent_task=None):
        print(colored('-------------------------', 'green'))
        print(colored(f"Implementing task {current_task_index + 1}...\n", "green"))
        print(sibling_tasks[current_task_index]['description'])
        print(colored('-------------------------', 'green'))
        convo_dev_task = AgentConvo(self)
        task_steps = convo_dev_task.send_message('development/task/breakdown.prompt', {
            "app_summary": self.project.high_level_summary,
            "clarification": [],
            "user_stories": self.project.user_stories,
            "user_tasks": self.project.user_tasks,
            "technologies": self.project.architecture,
            "array_of_objects_to_string": array_of_objects_to_string,
            # TODO remove hardcoded folder path
            "directory_tree": self.project.get_directory_tree(),
            "current_task_index": current_task_index,
            "sibling_tasks": sibling_tasks,
            "parent_task": parent_task,
        }, DEV_TASKS_BREAKDOWN)

        self.execute_task(convo_dev_task, task_steps)

    def execute_task(self, convo, task_steps):
        convo.save_branch('after_task_breakdown')
        for (i, step) in enumerate(task_steps):
            convo.load_branch('after_task_breakdown')
            if step['type'] == 'command':
                run_command_until_success(step['command'], step['command_timeout'], convo)
            elif step['type'] == 'code_change':
                print(f'Implementing code changes for `{step["code_change_description"]}`')
                code_monkey = CodeMonkey(self.project, self)
                updated_convo = code_monkey.implement_code_changes(convo, step['code_change_description'], i)
                self.test_code_changes(code_monkey, updated_convo)
            else:
                raise Exception('Step type must be either run_command or code_change.')
            
    def set_up_environment(self):
        self.project.current_step = 'environment_setup'
        self.convo_os_specific_tech = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return
        
        # ENVIRONMENT SETUP
        print(colored(f"Setting up the environment...\n", "green"))
        logger.info(f"Setting up the environment...")

        os_info = get_os_info()
        os_specific_techologies = self.convo_os_specific_tech.send_message('development/env_setup/specs.prompt',
            { "os_info": os_info, "technologies": self.project.architecture }, FILTER_OS_TECHNOLOGIES)

        for technology in os_specific_techologies:
            llm_response = self.convo_os_specific_tech.send_message('development/env_setup/install_next_technology.prompt',
                { 'technology': technology}, {
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
                installation_commands = self.convo_os_specific_tech.send_message('development/env_setup/unsuccessful_installation.prompt',
                    { 'technology': technology }, EXECUTE_COMMANDS)
                if installation_commands is not None:
                    for cmd in installation_commands:
                        run_command_until_success(cmd['command'], cmd['timeout'], self.convo_os_specific_tech)

        logger.info('The entire tech stack neede is installed and ready to be used.')

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "os_specific_techologies": os_specific_techologies, "newly_installed_technologies": [], "app_data": generate_app_data(self.project.args)
        })

        # ENVIRONMENT SETUP END

    def test_code_changes(self, code_monkey, convo):
        (test_type, command, automated_test_description, manual_test_description) = convo.send_message('development/task/step_check.prompt', {}, GET_TEST_TYPE)
        
        if test_type == 'command_test':
            run_command_until_success(command['command'], command['timeout'], convo)
        elif test_type == 'automated_test':
            code_monkey.implement_code_changes(convo, automated_test_description, 0)
        elif test_type == 'manual_test':
            # TODO make the message better
            self.project.ask_for_human_verification(
                'Message from Euclid: I need your help. Can you please test if this was successful?',
                manual_test_description
            )

    def implement_step(self, convo, step_index, type, description):
        # TODO remove hardcoded folder path
        directory_tree = self.project.get_directory_tree()
        step_details = convo.send_message('development/task/next_step.prompt', {
            'finished_steps': [],
            'step_description': description,
            'step_type': type,
            'directory_tree': directory_tree,
            'step_index': step_index
        }, EXECUTE_COMMANDS);
        if type == 'COMMAND':
            for cmd in step_details:
                run_command_until_success(cmd['command'], cmd['timeout'], convo)
        elif type == 'CODE_CHANGE':
            code_changes_details = get_step_code_changes()
            # TODO: give to code monkey for implementation
        pass
