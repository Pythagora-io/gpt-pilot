import platform
import uuid
from utils.style import (
    color_green,
    color_green_bold,
    color_red,
    color_red_bold,
    color_yellow_bold,
    color_blue_bold,
    color_white_bold
)
from helpers.exceptions.TokenLimitError import TokenLimitError
from const.code_execution import MAX_COMMAND_DEBUG_TRIES
from helpers.exceptions.TooDeepRecursionError import TooDeepRecursionError
from helpers.Debugger import Debugger
from utils.questionary import styled_text
from utils.utils import step_already_finished
from helpers.agents.CodeMonkey import CodeMonkey
from logger.logger import logger
from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo
from utils.utils import should_execute_step, array_of_objects_to_string, generate_app_data
from helpers.cli import run_command_until_success, execute_command_and_check_cli_response, running_processes, terminate_named_process
from const.function_calls import FILTER_OS_TECHNOLOGIES, EXECUTE_COMMANDS, GET_TEST_TYPE, IMPLEMENT_TASK
from database.database import save_progress, get_progress_steps, update_app_status
from utils.utils import get_os_info

ENVIRONMENT_SETUP_STEP = 'environment_setup'


class Developer(Agent):
    def __init__(self, project):
        super().__init__('full_stack_developer', project)
        self.run_command = None
        self.debugger = Debugger(self)

    def start_coding(self):
        if not self.project.finished:
            self.project.current_step = 'coding'
            update_app_status(self.project.args['app_id'], self.project.current_step)

            if self.project.skip_steps is None:
                self.project.skip_steps = False if ('skip_until_dev_step' in self.project.args and self.project.args['skip_until_dev_step'] == '0') else True

        # DEVELOPMENT
        print(color_green_bold("🚀 Now for the actual development...\n"))
        logger.info("Starting to create the actual code...")

        for i, dev_task in enumerate(self.project.development_plan):
            self.implement_task(i, dev_task)

        # DEVELOPMENT END
        self.project.dot_pilot_gpt.chat_log_folder(None)
        if not self.project.finished:
            self.project.current_step = 'finished'
            self.project.finished = True
            update_app_status(self.project.args['app_id'], self.project.current_step)
            message = 'The app is DONE!!! Yay...you can use it now.\n'
            logger.info(message)
            print(color_green_bold(message))
        else:
            message = 'Feature complete!\n'
            logger.info(message)
            print(color_green_bold(message))


    def implement_task(self, i, development_task=None):
        print(color_green_bold(f'Implementing task #{i + 1}: ') + color_green(f' {development_task["description"]}\n'))
        self.project.dot_pilot_gpt.chat_log_folder(i + 1)

        convo_dev_task = AgentConvo(self)
        convo_dev_task.send_message('development/task/breakdown.prompt', {
            "name": self.project.args['name'],
            "app_type": self.project.args['app_type'],
            "app_summary": self.project.project_description,
            "clarifications": self.project.clarifications,
            "user_stories": self.project.user_stories,
            "user_tasks": self.project.user_tasks,
            "technologies": self.project.architecture,
            "array_of_objects_to_string": array_of_objects_to_string,  # TODO check why is this here
            "directory_tree": self.project.get_directory_tree(True),
            "current_task_index": i,
            "development_tasks": self.project.development_plan,
            "files": self.project.get_all_coded_files(),
            "task_type": 'feature' if self.project.finished else 'app'
        })

        response = convo_dev_task.send_message('development/parse_task.prompt', {
            'running_processes': running_processes,
            'os': platform.system(),
        }, IMPLEMENT_TASK)
        task_steps = response['tasks']
        convo_dev_task.remove_last_x_messages(2)

        while True:
            result = self.execute_task(convo_dev_task,
                                     task_steps,
                                     development_task=development_task,
                                     continue_development=True,
                                     is_root_task=True)

            if result['success']:
                break

            if 'step_index' in result:
                result['running_processes'] = running_processes
                result['os'] = platform.system()
                step_index = result['step_index']
                result['completed_steps'] = task_steps[:step_index]
                result['current_step'] = task_steps[step_index]
                result['next_steps'] = task_steps[step_index + 1:]

                convo_dev_task.remove_last_x_messages(1)
                response = convo_dev_task.send_message('development/task/update_task.prompt', result, IMPLEMENT_TASK)
                task_steps = response['tasks']

            else:
                logger.warning('Testing at end of task failed')
                break

    def step_code_change(self, convo, step, i, test_after_code_changes):
        if step['type'] == 'code_change' and 'code_change_description' in step:
            # TODO this should be refactored so it always uses the same function call
            print(f'Implementing code changes for `{step["code_change_description"]}`')
            code_monkey = CodeMonkey(self.project, self)
            updated_convo = code_monkey.implement_code_changes(convo, step['code_change_description'], i)
            if test_after_code_changes:
                return self.test_code_changes(code_monkey, updated_convo)
            else:
                return { "success": True }

        elif step['type'] == 'code_change':
            # TODO fix this - the problem is in GPT response that sometimes doesn't return the correct JSON structure
            if 'code_change' not in step:
                data = step
            else:
                data = step['code_change']
            self.project.save_file(data)
            # TODO end
            return {"success": True}

    def step_command_run(self, convo, step, i, success_with_cli_response=False):
        logger.info('Running command: %s', step['command'])
        # TODO fix this - the problem is in GPT response that sometimes doesn't return the correct JSON structure
        if isinstance(step['command'], str):
            data = step
        else:
            data = step['command']
        # TODO END
        additional_message = 'Let\'s start with the step #0:\n\n' if i == 0 else f'So far, steps { ", ".join(f"#{j}" for j in range(i+1)) } are finished so let\'s do step #{i + 1} now.\n\n'

        command_id = data['command_id'] if 'command_id' in data else None
        success_message = data['success_message'] if 'success_message' in data else None

        return run_command_until_success(convo, data['command'],
                                         timeout=data['timeout'],
                                         command_id=command_id,
                                         success_message=success_message,
                                         additional_message=additional_message,
                                         success_with_cli_response=success_with_cli_response)

    def step_human_intervention(self, convo, step: dict):
        """
        :param convo:
        :param step: {'human_intervention_description': 'some description'}
        :return: {
          'success': bool
          'user_input': string_from_human
        }
        """
        logger.info('Human intervention needed%s: %s',
                    '' if self.run_command is None else f' for command `{self.run_command}`',
                    step['human_intervention_description'])

        while True:
            human_intervention_description = step['human_intervention_description']

            if self.run_command is not None:
                if (self.project.ipc_client_instance is None or self.project.ipc_client_instance.client is None):
                    human_intervention_description += color_yellow_bold('\n\nIf you want to run the app, just type "r" and press ENTER and that will run `' + self.run_command + '`')
                else:
                    print(self.run_command, type="run_command")

            response = self.project.ask_for_human_intervention('I need human intervention:',
                human_intervention_description,
                cbs={
                    'r': lambda conv: run_command_until_success(conv,
                                                                self.run_command,
                                                                # name the process so the LLM can kill it
                                                                command_id='app',
                                                                # If the app doesn't crash in the first 1st second
                                                                # assume it's good and leave it running.
                                                                # If timeout is None the conversation can't continue
                                                                timeout=1000,
                                                                force=True,
                                                                return_cli_response=True)
                },
                convo=convo)

            logger.info('human response: %s', response)
            if 'user_input' not in response:
                continue

            if response['user_input'] == 'continue':
                response['success'] = True
            else:
                response['success'] = self.debugger.debug(convo,
                                                   user_input=response['user_input'],
                                                   issue_description=step['human_intervention_description'])

            return response

    def step_test(self, convo, test_command):
        # TODO: don't re-run if it's already running
        should_rerun_command = convo.send_message('dev_ops/should_rerun_command.prompt', test_command)
        if should_rerun_command == 'NO':
            return { 'success': True }
        elif should_rerun_command == 'YES':
            logger.info('Re-running test command: %s', test_command)
            cli_response, llm_response = execute_command_and_check_cli_response(convo, test_command)
            logger.info('After running command llm_response: ' + llm_response)
            if llm_response == 'NEEDS_DEBUGGING':
                print(color_red('Got incorrect CLI response:'))
                print(cli_response)
                print(color_red('-------------------'))

            result = {'success': llm_response == 'DONE', 'cli_response': cli_response}
            if cli_response is None:
                result['user_input'] = llm_response
            else:
                result['llm_response'] = llm_response
            return result

    def task_postprocessing(self, convo, development_task, continue_development, task_result, last_branch_name):
        # TODO: why does `run_command` belong to the Developer class, rather than just being passed?
        #       ...It's set by execute_task() -> task_postprocessing(), but that is called by various sources.
        #       What is it at step_human_intervention()?
        self.run_command = convo.send_message('development/get_run_command.prompt', {})
        if self.run_command.startswith('`'):
            self.run_command = self.run_command[1:]
        if self.run_command.endswith('`'):
            self.run_command = self.run_command[:-1]

        if development_task is not None:
            convo.remove_last_x_messages(2)
            detailed_user_review_goal = convo.send_message('development/define_user_review_goal.prompt', {
                'os': platform.system()
            }, should_log_message=False)
            convo.remove_last_x_messages(2)

        try:
            if continue_development:
                continue_description = detailed_user_review_goal if detailed_user_review_goal is not None else None
                return self.continue_development(convo, last_branch_name, continue_description, development_task)
        except TooDeepRecursionError as e:
            logger.warning('Too deep recursion error. Call dev_help_needed() for human_intervention: %s', e.message)
            return self.dev_help_needed({"type": "human_intervention", "human_intervention_description": e.message})

        return task_result

    def should_retry_step_implementation(self, step, step_implementation_try):
        if step_implementation_try >= MAX_COMMAND_DEBUG_TRIES:
            self.dev_help_needed(step)

        print(color_red_bold('\n--------- LLM Reached Token Limit ----------'))
        print(color_red_bold('Can I retry implementing the entire development step?'))

        answer = ''
        while answer != 'y':
            answer = styled_text(
                self.project,
                'Type y/n'
            )

            logger.info("Retry step implementation? %s", answer)
            if answer == 'n':
                return self.dev_help_needed(step)

        return { "success": False, "retry": True }

    def dev_help_needed(self, step):

        if step['type'] == 'command':
            help_description = (color_red_bold('I tried running the following command but it doesn\'t seem to work:\n\n') +
                color_white_bold(step['command']['command']) +
                color_red_bold('\n\nCan you please make it work?'))
        elif step['type'] == 'code_change':
            help_description = step['code_change_description']
        elif step['type'] == 'human_intervention':
            help_description = step['human_intervention_description']

        # TODO remove this
        def extract_substring(s):
            start_idx = s.find('```')
            end_idx = s.find('```', start_idx + 3)

            if start_idx != -1 and end_idx != -1:
                return s[start_idx + 3:end_idx]
            else:
                return s
        # TODO end

        answer = ''
        while answer != 'continue':
            print(color_red_bold('\n----------------------------- I need your help ------------------------------'))
            print(extract_substring(str(help_description)))
            print(color_red_bold('\n-----------------------------------------------------------------------------'))
            answer = styled_text(
                self.project,
                'Once you\'re done, type "continue"?'
            )
            logger.info("help needed: %s", answer)

        return { "success": True, "user_input": answer }

    def execute_task(self, convo, task_steps, test_command=None, reset_convo=True,
                     test_after_code_changes=True, continue_development=False,
                     development_task=None, is_root_task=False):
        function_uuid = str(uuid.uuid4())
        convo.save_branch(function_uuid)

        for (i, step) in enumerate(task_steps):
            logger.info('---------- execute_task() step #%d: %s', i, step)

            result = None
            step_implementation_try = 0
            need_to_see_output = 'need_to_see_output' in step and step['need_to_see_output']

            while True:
                try:
                    if reset_convo:
                        convo.load_branch(function_uuid)

                    if step['type'] == 'command':
                        result = self.step_command_run(convo, step, i, success_with_cli_response=need_to_see_output)
                        # if need_to_see_output and 'cli_response' in result:
                        #     result['user_input'] = result['cli_response']

                    elif step['type'] == 'code_change':
                        result = self.step_code_change(convo, step, i, test_after_code_changes)

                    elif step['type'] == 'human_intervention':
                        result = self.step_human_intervention(convo, step)

                    elif step['type'] == 'kill_process':
                        terminate_named_process(step['kill_process'])
                        result = {'success': True}

                    logger.info('  step result: %s', result)

                    if (not result['success']) or need_to_see_output:
                        result['step'] = step
                        result['step_index'] = i
                        return result

                    if test_command is not None and ('check_if_fixed' not in step or step['check_if_fixed']):
                        logger.info('check_if_fixed: %s', test_command)
                        result = self.step_test(convo, test_command)
                        logger.info('task result: %s', result)
                        return result

                    break
                except TokenLimitError as e:
                    if is_root_task:
                        response = self.should_retry_step_implementation(step, step_implementation_try)
                        if 'retry' in response:
                            # TODO we can rewind this convo even more
                            convo.load_branch(function_uuid)
                            continue
                        elif 'success' in response:
                            result = response
                            break
                    else:
                        raise e
                except TooDeepRecursionError as e:
                    if is_root_task:
                        result = self.dev_help_needed(step)
                        break
                    else:
                        raise e

        result = { "success": True } # if all steps are finished, the task has been successfully implemented
        convo.load_branch(function_uuid)
        return self.task_postprocessing(convo, development_task, continue_development, result, function_uuid)

    def continue_development(self, iteration_convo, last_branch_name, continue_description='', development_task=None):
        while True:
            logger.info('Continue development, last_branch_name: %s', last_branch_name)
            iteration_convo.load_branch(last_branch_name)
            user_description = ('Here is a description of what should be working: \n\n' + color_blue_bold(continue_description) + '\n') \
                                if continue_description != '' else ''
            user_description = 'Can you check if the app works please? ' + user_description

            if self.project.ipc_client_instance is None or self.project.ipc_client_instance.client is None:
                user_description += color_yellow_bold('\n\nIf you want to run the app, just type "r" and press ENTER and that will run `' + self.run_command + '`')
            else:
                print(self.run_command, type="run_command")

            # continue_description = ''
            # TODO: Wait for a specific string in the output or timeout?
            response = self.project.ask_for_human_intervention(
                user_description,
                cbs={'r': lambda convo: run_command_until_success(convo, self.run_command,
                                                                  # name the process so the LLM can kill it
                                                                  command_id='app',
                                                                  # If the app doesn't crash in the first 1st second
                                                                  # assume it's good and leave it running.
                                                                  # If timeout is None the conversation can't continue
                                                                  timeout=1000,
                                                                  force=True,
                                                                  return_cli_response=True, is_root_task=True)},
                convo=iteration_convo,
                is_root_task=True)

            logger.info('response: %s', response)
            user_feedback = response['user_input'] if 'user_input' in response else None
            if user_feedback == 'continue':
                return { "success": True, "user_input": user_feedback }

            if user_feedback is not None:
                iteration_convo = AgentConvo(self)
                iteration_convo.send_message('development/iteration.prompt', {
                    "name": self.project.args['name'],
                    "app_type": self.project.args['app_type'],
                    "app_summary": self.project.project_description,
                    "clarifications": self.project.clarifications,
                    "user_stories": self.project.user_stories,
                    "user_tasks": self.project.user_tasks,
                    "technologies": self.project.architecture,
                    "array_of_objects_to_string": array_of_objects_to_string,  # TODO check why is this here
                    "directory_tree": self.project.get_directory_tree(True),
                    "current_task": development_task,
                    "development_tasks": self.project.development_plan,
                    "files": self.project.get_all_coded_files(),
                    "user_input": user_feedback,
                })

                # self.debugger.debug(iteration_convo, user_input=user_feedback)

                llm_response = iteration_convo.send_message('development/parse_task.prompt', {
                    'running_processes': running_processes,
                    'os': platform.system(),
                }, IMPLEMENT_TASK)
                iteration_convo.remove_last_x_messages(2)

                task_steps = llm_response['tasks']
                return self.execute_task(iteration_convo, task_steps, is_root_task=True)


    def set_up_environment(self):
        self.project.current_step = ENVIRONMENT_SETUP_STEP
        self.convo_os_specific_tech = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], ENVIRONMENT_SETUP_STEP)
        if step and not should_execute_step(self.project.args['step'], ENVIRONMENT_SETUP_STEP):
            step_already_finished(self.project.args, step)
            return

        user_input = ''
        while user_input.lower() != 'done':
            user_input = styled_text(self.project, 'Please set up your local environment so that the technologies listed can be utilized. When you\'re done, write "DONE"')
        save_progress(self.project.args['app_id'], self.project.current_step, {
            "os_specific_technologies": [], "newly_installed_technologies": [], "app_data": generate_app_data(self.project.args)
        })
        return
        # ENVIRONMENT SETUP
        print(color_green_bold("Setting up the environment...\n"))
        logger.info("Setting up the environment...")

        os_info = get_os_info()
        llm_response = self.convo_os_specific_tech.send_message('development/env_setup/specs.prompt',
            {
                "name": self.project.args['name'],
                "app_type": self.project.args['app_type'],
                "os_info": os_info,
                "technologies": self.project.architecture
            }, FILTER_OS_TECHNOLOGIES)

        os_specific_technologies = llm_response['technologies']
        for technology in os_specific_technologies:
            logger.info('Installing %s', technology)
            llm_response = self.install_technology(technology)

            # TODO: I don't think llm_response would ever be 'DONE'?
            if llm_response != 'DONE':
                llm_response = self.convo_os_specific_tech.send_message(
                    'development/env_setup/unsuccessful_installation.prompt',
                    {'technology': technology},
                    EXECUTE_COMMANDS)
                installation_commands = llm_response['commands']

                if installation_commands is not None:
                    for cmd in installation_commands:
                        run_command_until_success(self.convo_os_specific_tech, cmd['command'], timeout=cmd['timeout'])

        logger.info('The entire tech stack is installed and ready to be used.')

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "os_specific_technologies": os_specific_technologies,
            "newly_installed_technologies": [],
            "app_data": generate_app_data(self.project.args)
        })

        # ENVIRONMENT SETUP END

    # TODO: This is only called from the unreachable section of set_up_environment()
    def install_technology(self, technology):
        # TODO move the functions definitions to function_calls.py
        llm_response = self.convo_os_specific_tech.send_message(
            'development/env_setup/install_next_technology.prompt',
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
                                'description': 'Timeout in seconds for the approximate time this command takes to finish.',
                            }
                        },
                        'required': ['command', 'timeout'],
                    },
                }],
                'functions': {
                    'execute_command': lambda command, timeout: (command, timeout)
                }
            })

        cli_response, llm_response = execute_command_and_check_cli_response(self.convo_os_specific_tech, llm_response)

        return llm_response

    def test_code_changes(self, code_monkey, convo):
        logger.info('Testing code changes...')
        llm_response = convo.send_message('development/task/step_check.prompt', {}, GET_TEST_TYPE)
        test_type = llm_response['type']

        if test_type == 'command_test':
            command = llm_response['command']
            return run_command_until_success(convo, command['command'], timeout=command['timeout'])
        elif test_type == 'automated_test':
            # TODO get code monkey to implement the automated test
            pass
        elif test_type == 'manual_test':
            # TODO make the message better
            description = llm_response['manual_test_description']
            response = self.project.ask_for_human_intervention(
                'I need your help. Can you please test if this was successful?',
                description,
            )

            user_feedback = response['user_input']
            if user_feedback is not None and user_feedback != 'continue':
                debug_success = self.debugger.debug(convo, user_input=user_feedback, issue_description=description)
                return {'success': debug_success, 'user_input': user_feedback}
            else:
                return {'success': True, 'user_input': user_feedback}

    def implement_step(self, convo, step_index, type, description):
        logger.info('Implementing %s step #%d: %s', type, step_index, description)
        # TODO remove hardcoded folder path
        directory_tree = self.project.get_directory_tree(True)
        llm_response = convo.send_message('development/task/next_step.prompt', {
            'finished_steps': [],
            'step_description': description,
            'step_type': type,
            'directory_tree': directory_tree,
            'step_index': step_index
        }, EXECUTE_COMMANDS)

        step_details = llm_response['commands']

        if type == 'COMMAND':
            for cmd in step_details:
                run_command_until_success(convo, cmd['command'], timeout=cmd['timeout'])
        # elif type == 'CODE_CHANGE':
        #     code_changes_details = get_step_code_changes()
        #     # TODO: give to code monkey for implementation
        pass
