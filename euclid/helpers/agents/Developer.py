import json
import uuid
from termcolor import colored
from utils.questionary import styled_text
from helpers.files import update_file
from utils.utils import step_already_finished
from helpers.agents.CodeMonkey import CodeMonkey
from logger.logger import logger
from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo
from utils.utils import execute_step, array_of_objects_to_string, generate_app_data
from helpers.cli import build_directory_tree, run_command_until_success, execute_command_and_check_cli_response, debug
from const.function_calls import FILTER_OS_TECHNOLOGIES, DEVELOPMENT_PLAN, EXECUTE_COMMANDS, GET_TEST_TYPE, DEV_TASKS_BREAKDOWN, IMPLEMENT_TASK
from database.database import save_progress, get_progress_steps, save_file_description
from utils.utils import get_os_info
from helpers.cli import execute_command

class Developer(Agent):
    def __init__(self, project):
        super().__init__('full_stack_developer', project)

    def start_coding(self):
        self.project.current_step = 'coding'

        if self.project.skip_steps is None:
            self.project.skip_steps = False if ('skip_until_dev_step' in self.project.args and self.project.args['skip_until_dev_step'] == '0') else True

        # DEVELOPMENT
        print(colored(f"Ok, great, now, let's start with the actual development...\n", "green"))
        logger.info(f"Starting to create the actual code...")

        self.implement_task()

        # DEVELOPMENT END

        logger.info('The app is DONE!!! Yay...you can use it now.')

    def implement_task(self):
        print(colored('-------------------------', 'green', attrs=['bold']))
        # print(colored(f"Implementing task {current_task_index + 1}...\n", "green", attrs=['bold']))
        print(colored(f"Implementing task...\n", "green", attrs=['bold']))
        # print(colored(sibling_tasks[current_task_index]['description'], 'green', attrs=['bold']))
        # print(colored(task_explanation, 'green', attrs=['bold']))
        print(colored('-------------------------', 'green', attrs=['bold']))

        convo_dev_task = AgentConvo(self)
        task_description = convo_dev_task.send_message('development/task/breakdown.prompt', {
            "name": self.project.args['name'],
            "app_summary": self.project.project_description,
            "clarification": [],
            "user_stories": self.project.user_stories,
            # "user_tasks": self.project.user_tasks,
            "technologies": self.project.architecture,
            "array_of_objects_to_string": array_of_objects_to_string,
            "directory_tree": self.project.get_directory_tree(True),
            # "current_task_index": current_task_index,
            # "sibling_tasks": sibling_tasks,
            # "parent_task": parent_task,
        })

        task_steps = convo_dev_task.send_message('development/parse_task.prompt', {}, IMPLEMENT_TASK)
        convo_dev_task.remove_last_x_messages(2)
        self.execute_task(convo_dev_task, task_steps, continue_development=True)

    def execute_task(self, convo, task_steps, test_command=None, reset_convo=True, test_after_code_changes=True, continue_development=False):
        function_uuid = str(uuid.uuid4())
        convo.save_branch(function_uuid)

        for (i, step) in enumerate(task_steps):
            if reset_convo:
                convo.load_branch(function_uuid)

            if step['type'] == 'command':
                # TODO fix this - the problem is in GPT response that sometimes doesn't return the correct JSON structure
                if isinstance(step['command'], str):
                    data = step
                else:
                    data = step['command']
                # TODO END
                additional_message = 'Let\'s start with the step #0:\n\n' if i == 0 else f'So far, steps { ", ".join(f"#{j}" for j in range(i)) } are finished so let\'s do step #{i + 1} now.\n\n'
                run_command_until_success(data['command'], data['timeout'], convo, additional_message=additional_message)

            elif step['type'] == 'code_change' and 'code_change_description' in step:
                # TODO this should be refactored so it always uses the same function call
                print(f'Implementing code changes for `{step["code_change_description"]}`')
                code_monkey = CodeMonkey(self.project, self)
                updated_convo = code_monkey.implement_code_changes(convo, step['code_change_description'], i)
                if test_after_code_changes:
                    self.test_code_changes(code_monkey, updated_convo)

            elif step['type'] == 'code_change':
                # TODO fix this - the problem is in GPT response that sometimes doesn't return the correct JSON structure
                if 'code_change' not in step:
                    data = step
                else:
                    data = step['code_change']
                self.project.save_file(data)
                # TODO end

            elif step['type'] == 'human_intervention':
                user_feedback = self.project.ask_for_human_intervention('I need your help! Can you try debugging this yourself and let me take over afterwards? Here are the details about the issue:', step['human_intervention_description'])
                if user_feedback is not None:
                    debug(convo, user_input=user_feedback, issue_description=step['human_intervention_description'])

            if test_command is not None and ('check_if_fixed' not in step or step['check_if_fixed']):
                should_rerun_command = convo.send_message('dev_ops/should_rerun_command.prompt',
                    test_command)
                if should_rerun_command == 'NO':
                    return True
                elif should_rerun_command == 'YES':
                    cli_response, llm_response = execute_command_and_check_cli_response(test_command['command'], test_command['timeout'], convo)
                    if llm_response == 'NEEDS_DEBUGGING':
                        print(colored(f'Got incorrect CLI response:', 'red'))
                        print(cli_response)
                        print(colored('-------------------', 'red'))
                    if llm_response == 'DONE':
                        return True

        self.run_command = convo.send_message('development/get_run_command.prompt', {})

        if continue_development:
            self.continue_development(convo)

    def continue_development(self, iteration_convo):
        while True:
            user_feedback = self.project.ask_for_human_intervention(
                'Can you check if all this works? If you want to run the app, just type "r" and press ENTER',
                cbs={ 'r': lambda: run_command_until_success(self.run_command, None, iteration_convo, force=True) })

            if user_feedback == 'DONE':
                return True

            if user_feedback is not None:
                iteration_convo = AgentConvo(self)
                iteration_convo.send_message('development/iteration.prompt', {
                    "name": self.project.args['name'],
                    "app_summary": self.project.project_description,
                    "clarification": [],
                    "user_stories": self.project.user_stories,
                    # "user_tasks": self.project.user_tasks,
                    "technologies": self.project.architecture,
                    "array_of_objects_to_string": array_of_objects_to_string,
                    "directory_tree": self.project.get_directory_tree(True),
                    "files": self.project.get_all_coded_files(),
                    "user_input": user_feedback,
                })

                # debug(iteration_convo, user_input=user_feedback)

                task_steps = iteration_convo.send_message('development/parse_task.prompt', {}, IMPLEMENT_TASK)
                iteration_convo.remove_last_x_messages(2)
                self.execute_task(iteration_convo, task_steps, continue_development=False)

    
    def set_up_environment(self):
        self.project.current_step = 'environment_setup'
        self.convo_os_specific_tech = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return

        user_input = ''
        while user_input != 'DONE':
            user_input = styled_text(self.project, 'Please set up your local environment so that the technologies above can be utilized. When you\'re done, write "DONE"')
        save_progress(self.project.args['app_id'], self.project.current_step, {
            "os_specific_techologies": [], "newly_installed_technologies": [], "app_data": generate_app_data(self.project.args)
        })
        return
        # ENVIRONMENT SETUP
        print(colored(f"Setting up the environment...\n", "green"))
        logger.info(f"Setting up the environment...")

        os_info = get_os_info()
        os_specific_techologies = self.convo_os_specific_tech.send_message('development/env_setup/specs.prompt',
            { "name": self.project.args['name'], "os_info": os_info, "technologies": self.project.architecture }, FILTER_OS_TECHNOLOGIES)

        for technology in os_specific_techologies:
            # TODO move the functions definisions to function_calls.py
            cli_response, llm_response = self.convo_os_specific_tech.send_message('development/env_setup/install_next_technology.prompt',
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

            if llm_response != 'DONE':
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
        (test_type, command, automated_test_description, manual_test_description) = convo.send_message(
            'development/task/step_check.prompt',
            {},
            GET_TEST_TYPE)

        if test_type == 'command_test':
            run_command_until_success(command['command'], command['timeout'], convo)
        elif test_type == 'automated_test':
            code_monkey.implement_code_changes(convo, automated_test_description, 0)
        elif test_type == 'manual_test':
            # TODO make the message better
            user_feedback = self.project.ask_for_human_intervention(
                'Message from Euclid: I need your help. Can you please test if this was successful?',
                manual_test_description
            )
            if user_feedback is not None:
                debug(convo, user_input=user_feedback, issue_description=manual_test_description)

    def implement_step(self, convo, step_index, type, description):
        # TODO remove hardcoded folder path
        directory_tree = self.project.get_directory_tree(True)
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
