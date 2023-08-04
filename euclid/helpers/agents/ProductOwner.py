from termcolor import colored

from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from logger.logger import logger
from database.database import save_progress, save_app, get_progress_steps
from utils.utils import execute_step, generate_app_data, step_already_finished
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, get_additional_info_from_openai, \
    generate_messages_from_description
from const.llm import END_RESPONSE


class ProductOwner(Agent):
    def __init__(self, project):
        super().__init__('product_owner', project)

    def get_project_description(self):
        self.project.current_step = 'project_description'
        convo_project_description = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            self.project_description = step['summary']
            return step['summary']

        # PROJECT DESCRIPTION
        self.project.args['app_type'] = ask_for_app_type()

        save_app(self.project.args)

        main_prompt = ask_for_main_app_definition()

        high_level_messages = get_additional_info_from_openai(
            generate_messages_from_description(main_prompt, self.project.args['app_type']))

        high_level_summary = convo_project_description.send_message('utils/summary.prompt',
                                                {'conversation': '\n'.join(
                                                    [f"{msg['role']}: {msg['content']}" for msg in high_level_messages])})

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "prompt": main_prompt,
            "messages": high_level_messages,
            "summary": high_level_summary,
            "app_data": generate_app_data(self.project.args)
        })

        self.project_description = high_level_summary
        return high_level_summary
        # PROJECT DESCRIPTION END


    def get_user_stories(self):
        self.project.current_step = 'user_stories'
        self.convo_user_stories = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            self.convo_user_stories.messages = step['messages']
            return step['user_stories']

        # USER STORIES
        msg = f"Generating USER STORIES...\n"
        print(colored(msg, "green"))
        logger.info(msg)

        self.project.user_stories = self.convo_user_stories.continuous_conversation('user_stories/specs.prompt', {
            'prompt': self.project_description,
            'app_type': self.project.args['app_type'],
            'END_RESPONSE': END_RESPONSE
        })

        logger.info(f"Final user stories: {self.project.user_stories}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_stories": self.project.user_stories,
            "app_data": generate_app_data(self.project.args)
        })

        return self.project.user_stories
        # USER STORIES END

    def get_user_tasks(self):
        self.project.current_step = 'user_tasks'
        self.convo_user_stories.high_level_step = self.project.current_step

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return step['user_tasks']

        # USER TASKS
        msg = f"Generating USER TASKS...\n"
        print(colored(msg, "green"))
        logger.info(msg)

        self.project.user_tasks = self.convo_user_stories.continuous_conversation('user_stories/user_tasks.prompt',
            { 'END_RESPONSE': END_RESPONSE })

        logger.info(f"Final user tasks: {self.project.user_tasks}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_tasks": self.project.user_tasks,
            "app_data": generate_app_data(self.project.args)
        })

        return self.project.user_tasks
        # USER TASKS END
