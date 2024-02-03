import platform
import uuid
import re
import traceback

from const.code_execution import MAX_COMMAND_DEBUG_TRIES, MAX_RECURSION_LAYER
from const.function_calls import DEBUG_STEPS_BREAKDOWN
from const.messages import AFFIRMATIVE_ANSWERS, NEGATIVE_ANSWERS
from helpers.AgentConvo import AgentConvo
from helpers.exceptions import TokenLimitError
from helpers.exceptions import TooDeepRecursionError
from logger.logger import logger
from prompts.prompts import ask_user
from utils.exit import trace_code_event


class Debugger:
    def __init__(self, agent):
        self.agent = agent
        self.recursion_layer = 0

    def debug(self, convo, command=None, user_input=None, issue_description=None, is_root_task=False,
              ask_before_debug=False, task_steps=None, step_index=None):
        """
        Debug a conversation.

        Args:
            convo (AgentConvo): The conversation object.
            command (dict, optional): The command to debug. Default is None.
            user_input (str, optional): User input for debugging. Default is None.
                Should provide `command` or `user_input`.
            issue_description (str, optional): Description of the issue to debug. Default is None.
            ask_before_debug (bool, optional): True if we have to ask user for permission to start debugging.
            task_steps (list, optional): The steps of the task to debug. Default is None.
            step_index (int, optional): The index of the step to debug. Default is None.

        Returns:
            bool: True if debugging was successful, False otherwise.
        """
        logger.info('Debugging %s', command)
        self.recursion_layer += 1
        self.agent.project.current_task.add_debugging_task(self.recursion_layer, command, user_input, issue_description)
        if self.recursion_layer > MAX_RECURSION_LAYER:
            self.recursion_layer = 0
            # TooDeepRecursionError kills all debugging loops and goes back to the point where first debug was called
            # it does not retry initial step but instead calls dev_help_needed()
            raise TooDeepRecursionError()

        function_uuid = str(uuid.uuid4())
        convo.save_branch(function_uuid)
        success = False

        for i in range(MAX_COMMAND_DEBUG_TRIES):
            if success:
                break

            if ask_before_debug or i > 0:
                print('yes/no', type='button')
                answer = ask_user(self.agent.project, 'Can I start debugging this issue [Y/n/error details]?', require_some_input=False)
                if answer.lower() in NEGATIVE_ANSWERS:
                    self.recursion_layer -= 1
                    convo.load_branch(function_uuid)
                    return True
                if answer and answer.lower() not in AFFIRMATIVE_ANSWERS:
                    user_input = answer
                    self.agent.project.current_task.add_user_input_to_debugging_task(user_input)

            llm_response = convo.send_message('dev_ops/debug.prompt',
                {
                    'command': command['command'] if command is not None else None,
                    'user_input': user_input,
                    'issue_description': issue_description,
                    'task_steps': task_steps,
                    'step_index': step_index,
                    'os': platform.system()
                },
                DEBUG_STEPS_BREAKDOWN)

            completed_steps = []

            try:
                while True:
                    steps = completed_steps + llm_response['steps']

                    # TODO refactor to nicely get the developer agent
                    result = self.agent.project.developer.execute_task(
                        convo,
                        steps,
                        test_command=command,
                        test_after_code_changes=True,
                        continue_development=False,
                        is_root_task=is_root_task,
                        continue_from_step=len(completed_steps)
                    )

                    # in case one step failed or llm wants to see the output to determine the next steps
                    if 'step_index' in result:
                        result['os'] = platform.system()
                        step_index = result['step_index']
                        completed_steps = steps[:step_index+1]
                        result['completed_steps'] = completed_steps
                        result['current_step'] = steps[step_index]
                        result['next_steps'] = steps[step_index + 1:]
                        result['current_step_index'] = step_index

                        # Remove the previous debug plan and build a new one
                        convo.remove_last_x_messages(2)
                        # todo before updating task first check if update is needed
                        llm_response = convo.send_message('development/task/update_task.prompt', result,
                            DEBUG_STEPS_BREAKDOWN)
                    else:
                        success = result['success']
                        if not success:
                            convo.load_branch(function_uuid)
                            if 'cli_response' in result:
                                user_input = result['cli_response']
                                convo.messages[-2]['content'] = re.sub(
                                    r'(?<=The output was:\n\n).*?(?=\n\nThink about this output)',
                                    AgentConvo.escape_specials(result['cli_response']),
                                    convo.messages[-2]['content'],
                                    flags=re.DOTALL
                                )
                        break

            except TokenLimitError as e:
                # initial TokenLimitError is triggered by OpenAI API
                # TokenLimitError kills recursion loops 1 by 1 and reloads convo, so it can retry the same initial step
                if self.recursion_layer > 0:
                    convo.load_branch(function_uuid)
                    self.recursion_layer -= 1
                    raise e
                else:
                    trace_code_event('token-limit-error', {'error': traceback.format_exc()})
                    if not success:
                        convo.load_branch(function_uuid)
                    continue

            except TooDeepRecursionError as e:
                convo.load_branch(function_uuid)
                raise e

        convo.load_branch(function_uuid)
        self.recursion_layer -= 1
        return success
