import platform
import uuid
import re
import json

from const.messages import WHEN_USER_DONE, AFFIRMATIVE_ANSWERS, NEGATIVE_ANSWERS, STUCK_IN_LOOP, NONE_OF_THESE
from utils.exit import trace_code_event
from utils.style import (
    color_green,
    color_green_bold,
    color_red,
    color_red_bold,
    color_yellow_bold,
    color_cyan_bold,
    color_white_bold
)
from helpers.exceptions import TokenLimitError
from const.code_execution import MAX_COMMAND_DEBUG_TRIES, MAX_QUESTIONS_FOR_BUG_REPORT
from helpers.exceptions import TooDeepRecursionError
from helpers.Debugger import Debugger
from utils.questionary import styled_text
from utils.utils import step_already_finished
from helpers.agents.CodeMonkey import CodeMonkey
from logger.logger import logger
from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo
from utils.utils import should_execute_step, array_of_objects_to_string, generate_app_data
from helpers.cli import run_command_until_success, execute_command_and_check_cli_response
from const.function_calls import (EXECUTE_COMMANDS, GET_TEST_TYPE, IMPLEMENT_TASK, COMMAND_TO_RUN,
                                  ALTERNATIVE_SOLUTIONS, GET_BUG_REPORT_MISSING_DATA)
from database.database import save_progress, get_progress_steps, update_app_status
from utils.telemetry import telemetry
from prompts.prompts import ask_user

ENVIRONMENT_SETUP_STEP = 'environment_setup'


class Developer(Agent):
    def __init__(self, project):
        super().__init__('full_stack_developer', project)
        self.review_count = 0
        self.run_command = None
        self.save_dev_steps = True
        self.debugger = Debugger(self)

    def start_coding(self):
        if not self.project.finished:
            self.project.current_step = 'coding'
            update_app_status(self.project.args['app_id'], self.project.current_step)

        # DEVELOPMENT
        if not self.project.skip_steps:
            print(color_green_bold("🚀 Now for the actual development...\n"))
            logger.info("Starting to create the actual code...")

        total_tasks = len(self.project.development_plan)
        progress_thresholds = [50]  # Percentages of progress when documentation is created
        documented_thresholds = set()

        for i, dev_task in enumerate(self.project.development_plan):
            # don't create documentation for features
            if not self.project.finished:
                current_progress_percent = round((i / total_tasks) * 100, 2)

                for threshold in progress_thresholds:
                    if current_progress_percent > threshold and threshold not in documented_thresholds:
                        if not self.project.skip_steps:
                            self.project.technical_writer.document_project(current_progress_percent)
                        documented_thresholds.add(threshold)

            if self.project.tasks_to_load:
                task = self.project.tasks_to_load.pop(0)
                self.project.cleanup_list('dev_steps_to_load', task['id'])

                if len(self.project.tasks_to_load):
                    continue
                # if it is last task to load, execute it to check if it's finished
                else:
                    # if create_readme.prompt is after start of last task, that means task is fully done, so skip it
                    readme_dev_step = next((el for el in self.project.dev_steps_to_load if
                                                   'create_readme.prompt' in el.get('prompt_path', '')), None)

                    if len(self.project.development_plan) - 1 == i and readme_dev_step is not None:
                        self.project.cleanup_list('dev_steps_to_load', readme_dev_step['id'])
                        continue

            self.project.current_task.start_new_task(dev_task['description'], i + 1)
            self.implement_task(i, dev_task)
            telemetry.inc("num_tasks")

        # DEVELOPMENT END
        if not self.project.skip_steps:
            self.project.technical_writer.document_project(100)
            self.project.dot_pilot_gpt.chat_log_folder(None)

        if not self.project.finished:
            self.project.finished = True
            update_app_status(self.project.args['app_id'], self.project.current_step)
            message = 'The app is DONE!!! Yay...you can use it now.\n'
            logger.info(message)
            print(color_green_bold(message))
            if not self.project.skip_steps:
                telemetry.set("end_result", "success:initial-project")
                telemetry.send()
        else:
            message = 'Feature complete!\n'
            logger.info(message)
            print(color_green_bold(message))
            if not self.project.skip_steps:
                telemetry.set("end_result", "success:feature")
                telemetry.send()

    def implement_task(self, i, development_task=None):
        print(color_green_bold(f'Implementing task #{i + 1}: ') + color_green(f' {development_task["description"]}\n'))
        self.project.dot_pilot_gpt.chat_log_folder(i + 1)

        convo_dev_task = AgentConvo(self)
        # we get here only after all tasks but last one are loaded, so this must be final task
        if self.project.dev_steps_to_load and 'breakdown.prompt' in self.project.dev_steps_to_load[0]['prompt_path']:
            instructions = self.project.dev_steps_to_load[0]['llm_response']['text']
            convo_dev_task.messages = self.project.dev_steps_to_load[0]['messages']
            # remove breakdown from the head of dev_steps_to_load; if it's last, record it in checkpoint
            self.project.cleanup_list('dev_steps_to_load', int(self.project.dev_steps_to_load[0]['id']) + 1)
        else:
            instructions = convo_dev_task.send_message('development/task/breakdown.prompt', {
                "name": self.project.args['name'],
                "app_type": self.project.args['app_type'],
                "app_summary": self.project.project_description,
                "user_stories": self.project.user_stories,
                "user_tasks": self.project.user_tasks,
                "array_of_objects_to_string": array_of_objects_to_string,  # TODO check why is this here
                "directory_tree": self.project.get_directory_tree(True),
                "current_task_index": i,
                "development_tasks": self.project.development_plan,
                "files": self.project.get_all_coded_files(),
                "architecture": self.project.architecture,
                "technologies": self.project.system_dependencies + self.project.package_dependencies,
                "task_type": 'feature' if self.project.finished else 'app',
                "previous_features": self.project.previous_features,
                "current_feature": self.project.current_feature,
            })

        instructions_prefix = " ".join(instructions.split()[:5])
        instructions_postfix = " ".join(instructions.split()[-5:])
        if self.project.dev_steps_to_load and 'parse_task.prompt' in self.project.dev_steps_to_load[0]['prompt_path']:
            response = json.loads(self.project.dev_steps_to_load[0]['llm_response']['text'])
            convo_dev_task.messages = self.project.dev_steps_to_load[0]['messages']
            remove_last_x_messages = 1  # reason why 1 here is because in db we don't store llm_response in 'messages'
            # remove parse_task from the head of dev_steps_to_load; if it's last, record it in checkpoint
            last_parse_task_id = int(self.project.dev_steps_to_load[0]['id'])
            self.project.cleanup_list('dev_steps_to_load', last_parse_task_id + 1)
        else:
            response = convo_dev_task.send_message('development/parse_task.prompt', {
                'os': platform.system(),
                'instructions_prefix': instructions_prefix,
                'instructions_postfix': instructions_postfix,
            }, IMPLEMENT_TASK)
            remove_last_x_messages = 2
            last_parse_task_id = int(self.project.checkpoints['last_development_step']['id']) if self.project.checkpoints['last_development_step'] is not None else None

        steps = response['tasks']
        self.files_at_start_of_task = self.project.get_files_from_db_by_step_id(last_parse_task_id)
        self.modified_files = []
        convo_dev_task.remove_last_x_messages(remove_last_x_messages)

        completed_steps = []

        # This whole if statement is loading of project.
        # We want to skip to last iteration that user had in this task (in continue_development function) which is
        # last iteration.prompt. That prompt must be between current dev step and skip_until_dev_step or last dev
        # step in db.
        if self.project.dev_steps_to_load:
            # get last occurrence of iteration.prompt (used in continue_development)
            self.project.last_iteration = next((el for el in reversed(self.project.dev_steps_to_load) if
                                   'iteration.prompt' in el.get('prompt_path', '')), None)

            # detailed_user_review_goal is explanation for user how to review task (used in continue_development)
            self.project.last_detailed_user_review_goal = next(
                (el for el in reversed(self.project.dev_steps_to_load) if
                 'define_user_review_goal.prompt' in el.get('prompt_path', '')), None)

            # if no iteration.prompt then finish loading and continue execution normally
            if self.project.last_iteration is None and self.project.last_detailed_user_review_goal is None:
                self.project.finish_loading()
            else:
                # run_command is command to run app (used in continue_development)
                if self.run_command is None:
                    self.run_command = next(
                        (el for el in reversed(self.project.dev_steps_to_load) if
                         'get_run_command.prompt' in el.get('prompt_path', '')), None)
                    if self.run_command is not None:
                        self.run_command = json.loads(self.run_command['llm_response']['text'])['command']

                ids = [
                    self.project.last_iteration['id'] if self.project.last_iteration else None,
                    self.project.last_detailed_user_review_goal['id'] if self.project.last_detailed_user_review_goal else None
                ]
                # remove latest ID (which can be last_iteration or last_detailed_user_review_goal) from the head of
                # dev_steps_to_load; if it's last, record it in checkpoint
                self.project.cleanup_list('dev_steps_to_load', max(id for id in ids if id is not None))

        while True:
            result = self.execute_task(convo_dev_task,
                                       steps,
                                       development_task=development_task,
                                       continue_development=True,
                                       is_root_task=True,
                                       continue_from_step=len(completed_steps))

            if result['success']:
                break

            if 'step_index' in result:
                result['os'] = platform.system()
                step_index = result['step_index']
                completed_steps = steps[:step_index + 1]
                result['completed_steps'] = completed_steps
                result['current_step'] = steps[step_index]
                result['next_steps'] = steps[step_index + 1:]
                result['current_step_index'] = step_index

                convo_dev_task.remove_last_x_messages(2)
                # todo before updating task first check if update is needed
                response = convo_dev_task.send_message('development/task/update_task.prompt', result, IMPLEMENT_TASK)
                steps = completed_steps + response['tasks']

            else:
                logger.warning('Testing at end of task failed')
                break

    def step_delete_file(self, convo, step, i, test_after_code_changes):
        """
        Delete a file from the project.

        This doesn't delete the files yet, but measures how often LLM
        neads to clean up (delete) entire files.
        """
        data = step['delete_file']
        trace_code_event(
            "delete-file-stub",
            data,
        )
        return {"success": True}


    def step_save_file(self, convo, step, i, test_after_code_changes):
        # Backwards
        if 'modify_file' in step:
            step['save_file'] = step.pop('modify_file')
        elif 'code_change' in step:
            step['save_file'] = step.pop('code_change')

        data = step['save_file']
        code_monkey = CodeMonkey(self.project)
        code_monkey.implement_code_changes(convo, data)
        return {"success": True}

    def step_command_run(self, convo, task_steps, i, success_with_cli_response=False):
        step = task_steps[i]
        logger.info('Running command: %s', step['command'])
        data = step['command']
        additional_message = ''  # 'Let\'s start with the step #0:\n' if i == 0 else f'So far, steps { ", ".join(f"#{j}" for j in range(i+1)) } are finished so let\'s do step #{i + 1} now.\n'

        command_id = data['command_id'] if 'command_id' in data else None
        success_message = data['success_message'] if 'success_message' in data else None

        return run_command_until_success(convo, data['command'],
                                         timeout=data['timeout'],
                                         command_id=command_id,
                                         success_message=success_message,
                                         additional_message=additional_message,
                                         success_with_cli_response=success_with_cli_response,
                                         task_steps=task_steps,
                                         step_index=i)

    def step_human_intervention(self, convo, task_steps: list, step_index):
        """
        :param convo:
        :param task_steps: list of steps
        :param step_index: index of the step that needs human intervention
        :return: {
          'success': bool
          'user_input': string_from_human
        }
        """
        step = task_steps[step_index]
        logger.info('Human intervention needed%s: %s',
                    '' if self.run_command is None else f' for command `{self.run_command}`',
                    step['human_intervention_description'] if 'human_intervention_description' in step else '')

        while True:
            human_intervention_description = step['human_intervention_description'] if 'human_intervention_description' in step else ''

            if not self.run_command:
                self.get_run_command(convo)

            if self.run_command:
                if self.project.check_ipc():
                    print(self.run_command, type='run_command')
                else:
                    human_intervention_description += color_yellow_bold(
                        '\n\nIf you want to run the app, just type "r" and press ENTER and that will run `' + self.run_command + '`')

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
                                                                timeout=None,
                                                                force=True,
                                                                return_cli_response=True,
                                                                task_steps=task_steps,
                                                                step_index=step_index)
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
                                                          issue_description=step['human_intervention_description'] if 'human_intervention_description' in step else '',
                                                          task_steps=task_steps,
                                                          step_index=step_index)
                # TODO add review

            return response

    def step_test(self, convo, test_command, task_steps=None, step_index=None):
        # TODO: don't re-run if it's already running
        should_rerun_command = convo.send_message('dev_ops/should_rerun_command.prompt', test_command)
        if should_rerun_command == 'NO':
            return {'success': True}
        elif should_rerun_command == 'YES':
            logger.info('Re-running test command: %s', test_command)
            cli_response, llm_response = execute_command_and_check_cli_response(convo,
                                                                                test_command,
                                                                                task_steps=task_steps,
                                                                                step_index=step_index)
            logger.info('After running command llm_response: ' + llm_response)
            if llm_response == 'BUG':
                print(color_red('Got incorrect CLI response:'))
                print(cli_response)
                print(color_red('-------------------'))

            result = {
                'success': llm_response in ["DONE", "SKIP"],
                'cli_response': cli_response
            }
            if cli_response is None:
                result['user_input'] = llm_response
            else:
                result['llm_response'] = llm_response
            return result

    def get_run_command(self, convo):
        llm_response = convo.send_message('development/get_run_command.prompt', {}, COMMAND_TO_RUN)
        self.run_command = llm_response['command']

        # Pattern for triple backtick code block with optional language
        triple_backtick_pattern = r"```(?:\w+\n)?(.*?)```"
        triple_match = re.search(triple_backtick_pattern, self.run_command, re.DOTALL)
        # Pattern for single backtick
        single_backtick_pattern = r"`(.*?)`"
        single_match = re.search(single_backtick_pattern, self.run_command, re.DOTALL)

        if triple_match:
            self.run_command = triple_match.group(1).strip()
        elif single_match:
            self.run_command = single_match.group(1).strip()

    def task_postprocessing(self, convo, development_task, continue_development, task_result, last_branch_name):
        if self.project.last_detailed_user_review_goal is None:
            self.get_run_command(convo)

            if development_task is not None:
                convo.remove_last_x_messages(2)
                detailed_user_review_goal = convo.send_message('development/define_user_review_goal.prompt', {
                    'os': platform.system()
                }, should_log_message=False)
                convo.remove_last_x_messages(2)
        else:
            detailed_user_review_goal = self.project.last_detailed_user_review_goal['llm_response']['text']

        try:
            if continue_development and detailed_user_review_goal and detailed_user_review_goal != "DONE":
                continue_description = detailed_user_review_goal if detailed_user_review_goal is not None else None
                return self.continue_development(convo, last_branch_name, continue_description, development_task)
        except TooDeepRecursionError as e:
            logger.warning('Too deep recursion error. Call dev_help_needed() for human_intervention: %s', e.message)
            return self.dev_help_needed({"type": "human_intervention", "human_intervention_description": e.message})

        return task_result

    def should_retry_step_implementation(self, step, step_implementation_try):
        if step_implementation_try >= MAX_COMMAND_DEBUG_TRIES:
            return self.dev_help_needed(step)

        print(color_red_bold('\n--------- LLM Reached Token Limit ----------'))
        print(color_red_bold('Can I retry implementing the entire development step?'))

        answer = None
        while answer is None or answer.lower() not in AFFIRMATIVE_ANSWERS:
            print('yes/no', type='buttons-only')
            answer = styled_text(
                self.project,
                'Type y/n'
            )

            logger.info("Retry step implementation? %s", answer)
            if answer.lower() in NEGATIVE_ANSWERS:
                return self.dev_help_needed(step)

        return {"success": False, "retry": True}

    def dev_help_needed(self, step):

        if step['type'] == 'command':
            help_description = (
                    color_red_bold('I tried running the following command but it doesn\'t seem to work:\n\n') +
                    color_white_bold(step['command']['command']) +
                    color_red_bold('\n\nCan you please make it work?'))
        elif step['type'] == 'human_intervention':
            help_description = step['human_intervention_description']
        else:
            # This should never happen on steps other than command and HI, but just in case
            help_description = step['type']

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
        while answer.lower() != 'continue':
            print(color_red_bold('\n----------------------------- I need your help ------------------------------'))
            print(color_red('\nHere are instructions for the issue I did not manage to solve:'))
            print(extract_substring(str(help_description)))
            print(color_red_bold('\n-----------------------------------------------------------------------------'))
            print('continue', type='buttons-only')
            answer = ask_user(
                self.project,
                WHEN_USER_DONE,
            )
            logger.info("help needed: %s", answer)

        return {"success": True, "user_input": answer}

    def execute_task(self, convo, task_steps, test_command=None, reset_convo=True,
                     test_after_code_changes=True, continue_development=False,
                     development_task=None, is_root_task=False, continue_from_step=0):
        function_uuid = str(uuid.uuid4())
        convo.save_branch(function_uuid)

        for (i, step) in enumerate(task_steps):
            if (step['type'] in ['save_file', 'code_change', 'modify_file'] and
                    'path' in step[step['type']] and
                    step[step['type']]['path'] not in self.modified_files):
                self.modified_files.append(step[step['type']]['path'])
            # This means we are still loading the project and have all the steps until last iteration
            if self.project.last_iteration is not None or self.project.last_detailed_user_review_goal is not None:
                continue

            # Skip steps before continue_from_step
            if i < continue_from_step:
                continue
            logger.info('---------- execute_task() step #%d: %s', i, step)
            # this if statement is for current way of loading app,
            # once we move to backwards compatibility if statement can be removed
            if not self.project.skip_steps:
                self.project.current_task.inc('steps')

            result = None
            step_implementation_try = 0
            need_to_see_output = 'need_to_see_output' in step and step['need_to_see_output']

            while True:
                try:
                    if reset_convo:
                        convo.load_branch(function_uuid)

                    if step['type'] == 'command':
                        result = self.step_command_run(convo, task_steps, i, success_with_cli_response=need_to_see_output)
                        # if need_to_see_output and 'cli_response' in result:
                        #     result['user_input'] = result['cli_response']

                    elif step['type'] in ['save_file', 'modify_file', 'code_change']:
                        result = self.step_save_file(convo, step, i, test_after_code_changes)

                    elif step['type'] == 'delete_file':
                        result = self.step_delete_file(convo, step, i, test_after_code_changes)

                    elif step['type'] == 'human_intervention':
                        result = self.step_human_intervention(convo, task_steps, i)

                    # TODO background_command - if we run commands in background we should have way to kill processes
                    #  and that should be added to function_calls.py DEBUG_STEPS_BREAKDOWN and IMPLEMENT_TASK
                    # elif step['type'] == 'kill_process':
                    #     terminate_named_process(step['kill_process'])
                    #     result = {'success': True}

                    logger.info('  step result: %s', result)

                    if (not result['success']) or (need_to_see_output and result.get("user_input") != "SKIP"):
                        result['step'] = step
                        result['step_index'] = i
                        return result

                    if test_command is not None and ('check_if_fixed' not in step or step['check_if_fixed']):
                        logger.info('check_if_fixed: %s', test_command)
                        result = self.step_test(convo, test_command, task_steps=task_steps, step_index=i)
                        logger.info('task result: %s', result)
                        return result

                    break
                except TokenLimitError as e:
                    if is_root_task:
                        response = self.should_retry_step_implementation(step, step_implementation_try)
                        if 'retry' in response:
                            # TODO we can rewind this convo even more
                            step_implementation_try += 1
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

        result = {"success": True}  # if all steps are finished, the task has been successfully implemented... NOT!
        convo.load_branch(function_uuid)
        return self.task_postprocessing(convo, development_task, continue_development, result, function_uuid)

    def continue_development(self, iteration_convo, last_branch_name, continue_description='', development_task=None):
        llm_solutions = self.project.last_iteration['prompt_data']['previous_solutions'] if (self.project.last_iteration and 'previous_solutions' in self.project.last_iteration['prompt_data']) else []
        alternative_solutions_to_current_issue = self.project.last_iteration['prompt_data']['alternative_solutions_to_current_issue'] if (self.project.last_iteration and 'alternative_solutions_to_current_issue' in self.project.last_iteration['prompt_data']) else []
        tried_alternative_solutions_to_current_issue = self.project.last_iteration['prompt_data']['tried_alternative_solutions_to_current_issue'] if (self.project.last_iteration and 'tried_alternative_solutions_to_current_issue' in self.project.last_iteration['prompt_data']) else []
        next_solution_to_try = None
        iteration_count = self.project.last_iteration['prompt_data']['iteration_count'] if (self.project.last_iteration and 'iteration_count' in self.project.last_iteration['prompt_data']) else 0
        while True:
            self.user_feedback = llm_solutions[-1]['user_feedback'] if len(llm_solutions) > 0 else None
            review_successful = self.project.skip_steps or self.review_task()
            if not review_successful and self.review_count < 3:
                continue
            iteration_count += 1
            logger.info('Continue development, last_branch_name: %s', last_branch_name)
            if last_branch_name in iteration_convo.branches.keys():  # if user_feedback is not None we create new convo
                iteration_convo.load_branch(last_branch_name)
            user_description = ('Here is a description of what should be working: \n\n' + color_cyan_bold(
                continue_description) + '\n') \
                if continue_description != '' else ''
            user_description = 'Can you check if the app works please? ' + user_description

            if self.run_command:
                if self.project.check_ipc():
                    print(self.run_command, type='run_command')
                else:
                    user_description += color_yellow_bold(
                        '\n\nIf you want to run the app, just type "r" and press ENTER and that will run `' + self.run_command + '`')

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
                                                                  timeout=None,
                                                                  force=True,
                                                                  return_cli_response=True, is_root_task=True)},
                convo=iteration_convo,
                is_root_task=True,
                add_loop_button=iteration_count > 3)

            logger.info('response: %s', response)
            self.review_count = 0
            user_feedback = response['user_input'] if 'user_input' in response else None
            if user_feedback == 'continue':
                # self.project.remove_debugging_logs_from_all_files()
                return {"success": True, "user_input": user_feedback}

            if user_feedback is not None:
                user_feedback = self.bug_report_generator(user_feedback)
                stuck_in_loop = user_feedback.startswith(STUCK_IN_LOOP)
                if stuck_in_loop:
                    # Remove the STUCK_IN_LOOP prefix from the user feedback
                    user_feedback = user_feedback[len(STUCK_IN_LOOP):]
                    stuck_in_loop = False
                    if len(alternative_solutions_to_current_issue) > 0:
                        next_solution_to_try_index = self.ask_user_for_next_solution(alternative_solutions_to_current_issue)
                        if next_solution_to_try_index == NONE_OF_THESE:
                            next_solution_to_try = self.get_alternative_solutions(development_task, user_feedback, llm_solutions, tried_alternative_solutions_to_current_issue + alternative_solutions_to_current_issue)
                        else:
                            next_solution_to_try = alternative_solutions_to_current_issue.pop(next_solution_to_try_index - 1)
                    else:
                        description_of_tried_solutions, alternative_solutions_to_current_issue, next_solution_to_try = self.get_alternative_solutions(development_task, user_feedback, llm_solutions, tried_alternative_solutions_to_current_issue)
                        if len(tried_alternative_solutions_to_current_issue) == 0:
                            tried_alternative_solutions_to_current_issue.append(description_of_tried_solutions)

                    tried_alternative_solutions_to_current_issue.append(next_solution_to_try)

                iteration_convo = AgentConvo(self)
                iteration_description = iteration_convo.send_message('development/iteration.prompt', {
                    "name": self.project.args['name'],
                    "app_type": self.project.args['app_type'],
                    "app_summary": self.project.project_description,
                    "user_stories": self.project.user_stories,
                    "user_tasks": self.project.user_tasks,
                    "architecture": self.project.architecture,
                    "technologies": self.project.system_dependencies + self.project.package_dependencies,
                    "array_of_objects_to_string": array_of_objects_to_string,  # TODO check why is this here
                    "directory_tree": self.project.get_directory_tree(True),
                    "current_task": development_task,
                    "development_tasks": self.project.development_plan,
                    "files": self.project.get_all_coded_files(),
                    "user_input": user_feedback,
                    "previous_solutions": llm_solutions[-3:],
                    "next_solution_to_try": next_solution_to_try,
                    "alternative_solutions_to_current_issue": alternative_solutions_to_current_issue,
                    "tried_alternative_solutions_to_current_issue": tried_alternative_solutions_to_current_issue,
                    "iteration_count": iteration_count,
                    "previous_features": self.project.previous_features,
                    "current_feature": self.project.current_feature,
                })

                llm_solutions.append({
                    "user_feedback": user_feedback,
                    "llm_proposal": iteration_description
                })

                instructions_prefix = " ".join(iteration_description.split()[:5])
                instructions_postfix = " ".join(iteration_description.split()[-5:])

                llm_response = iteration_convo.send_message('development/parse_task.prompt', {
                    'os': platform.system(),
                    'instructions_prefix': instructions_prefix,
                    'instructions_postfix': instructions_postfix,
                }, IMPLEMENT_TASK)
                iteration_convo.remove_last_x_messages(2)

                task_steps = llm_response['tasks']
                self.execute_task(iteration_convo, task_steps, is_root_task=True)

    def bug_report_generator(self, user_feedback):
        """
        Generate a bug report from the user feedback.

        :param user_feedback: The user feedback.
        :return: The bug report.
        """
        bug_report_convo = AgentConvo(self)
        function_uuid = str(uuid.uuid4())
        bug_report_convo.save_branch(function_uuid)
        questions_and_answers = []
        while True:
            llm_response = bug_report_convo.send_message('development/bug_report.prompt', {
                "user_feedback": user_feedback,
                "app_summary": self.project.project_description,
                "files": self.project.get_all_coded_files(),
                "questions_and_answers": questions_and_answers,
            }, GET_BUG_REPORT_MISSING_DATA)

            missing_data = llm_response['missing_data']
            if len(missing_data) == 0:
                break

            length_before = len(questions_and_answers)
            for missing_data_item in missing_data:
                if self.project.check_ipc():
                    print(missing_data_item['question'], type='verbose')
                    print('continue/skip question', type='button')
                    if self.run_command:
                            print(self.run_command, type='run_command')

                answer = ask_user(self.project, missing_data_item['question'], require_some_input=False)
                if answer.lower() == 'skip question' or answer.lower() == '' or answer.lower() == 'continue':
                    continue

                questions_and_answers.append({
                    "question": missing_data_item['question'],
                    "answer": answer
                })

            # if user skips all questions or if we got more than 4 answers, we don't want to get stuck in infinite loop
            if length_before == len(questions_and_answers) or len(questions_and_answers) >= MAX_QUESTIONS_FOR_BUG_REPORT:
                break
            bug_report_convo.load_branch(function_uuid)

        if len(questions_and_answers):
            bug_report_summary_convo = AgentConvo(self)
            user_feedback = bug_report_summary_convo.send_message('development/bug_report_summary.prompt', {
                "app_summary": self.project.project_description,
                "user_feedback": user_feedback,
                "questions_and_answers": questions_and_answers,
            })

        return user_feedback

    def review_task(self):
        """
        Review all task changes and refactor big files.
        :return: bool - True if the task changes passed review, False if not
        """
        self.review_count += 1
        review_result = self.review_code_changes()
        refactoring_done = self.refactor_code()
        if refactoring_done or review_result['implementation_needed']:
            review_result = self.review_code_changes()

        return review_result['success']

    def review_code_changes(self):
        """
        Review the code changes and ask for human intervention if needed

        :return: dict - {
            'success': bool,
            'implementation_needed': bool
        }
        """
        review_convo = AgentConvo(self)
        files = [
            file_dict for file_dict in self.project.get_all_coded_files()
            if any(file_dict['full_path'].endswith(modified_file) for modified_file in self.modified_files)
        ]
        files_at_start_of_task = [
            file_dict for file_dict in self.files_at_start_of_task
            if any(file_dict['full_path'].endswith(modified_file) for modified_file in self.modified_files)
        ]
        review = review_convo.send_message('development/review_task.prompt', {
            "name": self.project.args['name'],
            "app_summary": self.project.project_description,
            "tasks": self.project.development_plan,
            "current_task": self.project.current_task.data.get('task_description'),
            "files": files,
            "user_input": self.user_feedback,
            "modified_files": self.modified_files,
            "files_at_start_of_task": files_at_start_of_task,
            "previous_features": self.project.previous_features,
            "current_feature": self.project.current_feature,
        })

        instructions_prefix = " ".join(review.split()[:5])
        instructions_postfix = " ".join(review.split()[-5:])

        if 'DONE' in instructions_postfix:
            return {
                'success': True,
                'implementation_needed': False,
            }

        llm_response = review_convo.send_message('development/parse_task.prompt', {
            'os': platform.system(),
            'instructions_prefix': instructions_prefix,
            'instructions_postfix': instructions_postfix,
        }, IMPLEMENT_TASK)

        task_steps = llm_response['tasks']
        result = self.execute_task(review_convo, task_steps)
        return {
            'success': result['success'] if 'success' in result else False,
            'implementation_needed': True,
        }

    def refactor_code(self):
        """
        Refactor the code if needed
        :return: bool - True if the code refactoring was done
        """
        # todo refactor code
        return False

    def set_up_environment(self):
        self.project.current_step = ENVIRONMENT_SETUP_STEP
        self.convo_os_specific_tech = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], ENVIRONMENT_SETUP_STEP)
        if step and not should_execute_step(self.project.args['step'], ENVIRONMENT_SETUP_STEP):
            step_already_finished(self.project.args, step)
            return

        print(color_green_bold("Setting up the environment...\n"))
        logger.info("Setting up the environment...")

        for dependency in self.project.system_dependencies:
            if 'description' in dependency:
                dep_text = f"{dependency['name']} ({dependency['description']})"
            else:
                dep_text = dependency['name']

            logger.info('Checking %s', dependency)
            llm_response = self.check_system_dependency(dependency)

            if llm_response == 'DONE':
                print(color_green_bold(f"✅ {dep_text} is available."))
            else:
                if dependency["required_locally"]:
                    remedy_text = "Please install it before proceeding with your app."
                else:
                    remedy_text = "If you want to use it locally, you should install it before proceeding."
                print(color_red_bold(f"❌ {dep_text} is not available. {remedy_text}"))

                print('continue', type='buttons-only')
                ask_user(
                    self.project,
                    "When you're ready to proceed, press ENTER to continue.",
                    require_some_input=False,
                )

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "os_specific_technologies": self.project.system_dependencies,
            "newly_installed_technologies": [],
            "app_data": generate_app_data(self.project.args)
        })

        # ENVIRONMENT SETUP END

    def check_system_dependency(self, dependency):
        convo = AgentConvo(self)
        cli_response, llm_response = execute_command_and_check_cli_response(
            convo,
            {
                "command": dependency["test"],
                "timeout": 10000,
            }
        )
        return llm_response

    def test_code_changes(self, convo, task_steps=None, step_index=None):
        """
        :param convo: AgentConvo
        :param task_steps: list of steps
        :param step_index: index of the step that is being implemented
        :return: {
          'success': bool
          'user_input': string_from_human
        }
        """
        return {"success": True}
        logger.info('Testing code changes...')
        llm_response = convo.send_message('development/task/step_check.prompt', {}, GET_TEST_TYPE)
        test_type = llm_response['type']

        if test_type == 'command_test':
            command = llm_response['command']
            return run_command_until_success(convo, command['command'], timeout=command['timeout'],
                                             task_steps=task_steps, step_index=step_index)
        elif test_type == 'automated_test':
            # TODO get code monkey to implement the automated test
            pass
        elif test_type == 'manual_test':
            # TODO make the message better
            return_value = {'success': False}
            while not return_value['success']:
                description = llm_response['manual_test_description']
                response = self.project.ask_for_human_intervention(
                    'I need your help. Can you please test if this was successful?',
                    description,
                )

                user_feedback = response['user_input']
                if user_feedback is not None and user_feedback != 'continue':
                    self.debugger.debug(convo, user_input=user_feedback, issue_description=description,
                                        task_steps=task_steps, step_index=step_index)
                else:
                    return_value = {'success': True, 'user_input': user_feedback}

            return return_value

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

    def get_alternative_solutions(self, development_task, user_feedback, previous_solutions, tried_alternative_solutions_to_current_issue):
        convo = AgentConvo(self)
        response = convo.send_message('development/get_alternative_solutions.prompt', {
            "name": self.project.args['name'],
            "app_type": self.project.args['app_type'],
            "app_summary": self.project.project_description,
            "architecture": self.project.architecture,
            "technologies": self.project.system_dependencies + self.project.package_dependencies,
            "directory_tree": self.project.get_directory_tree(True),
            "current_task": development_task,
            "development_tasks": self.project.development_plan,
            "files": self.project.get_all_coded_files(),
            "user_input": user_feedback,
            "previous_solutions": previous_solutions,
            "tried_alternative_solutions_to_current_issue": tried_alternative_solutions_to_current_issue,
            "previous_features": self.project.previous_features,
            "current_feature": self.project.current_feature,
        }, ALTERNATIVE_SOLUTIONS)

        next_solution_to_try_index = self.ask_user_for_next_solution(response['alternative_solutions'])
        if isinstance(next_solution_to_try_index, str) and next_solution_to_try_index == NONE_OF_THESE:
            return self.get_alternative_solutions(development_task, user_feedback, previous_solutions, tried_alternative_solutions_to_current_issue + response['alternative_solutions'])

        next_solution_to_try = response['alternative_solutions'].pop(next_solution_to_try_index - 1)

        return response['description_of_tried_solutions'], response['alternative_solutions'], next_solution_to_try

    def ask_user_for_next_solution(self, alternative_solutions):
        solutions_indices_as_strings = [str(i + 1) for i in range(len(alternative_solutions))]
        string_for_buttons = '/'.join(solutions_indices_as_strings) + '/' + (NONE_OF_THESE[0].upper() + NONE_OF_THESE[1:])

        description_of_solutions = '\n\n'.join([f"{index + 1}: {sol}" for index, sol in enumerate(alternative_solutions)])
        print(string_for_buttons, type='button')
        next_solution_to_try_index = ask_user(self.project, 'Choose which solution would you like GPT Pilot to try next?',
                                              require_some_input=False,
                                              hint=description_of_solutions)

        if next_solution_to_try_index in solutions_indices_as_strings:
            next_solution_to_try_index = int(next_solution_to_try_index)
        elif next_solution_to_try_index.lower() == NONE_OF_THESE:
            next_solution_to_try_index = NONE_OF_THESE
        else:
            next_solution_to_try_index = 1

        return next_solution_to_try_index
