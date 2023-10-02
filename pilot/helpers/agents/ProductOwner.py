import json
from utils.style import green_bold
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from logger.logger import logger
from database.database import save_progress, save_app, get_progress_steps
from utils.utils import should_execute_step, generate_app_data, step_already_finished, clean_filename
from utils.files import setup_workspace
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, get_additional_info_from_openai, \
    generate_messages_from_description, ask_user
from const.llm import END_RESPONSE

PROJECT_DESCRIPTION_STEP = 'project_description'
USER_STORIES_STEP = 'user_stories'
USER_TASKS_STEP = 'user_tasks'


class ProductOwner(Agent):
    def __init__(self, project):
        super().__init__('product_owner', project)

    def get_project_description(self):
        # TODO: why save the project before user has even committed to a name & description?
        # The UI saves a record as soon as the click "Create Project" button
        self.project.app = save_app(self.project)
        self.project.current_step = PROJECT_DESCRIPTION_STEP

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], PROJECT_DESCRIPTION_STEP)
        if step and not should_execute_step(self.project.args['step'], PROJECT_DESCRIPTION_STEP):
            step_already_finished(self.project.args, step)
            self.project.root_path = setup_workspace(self.project.args)
            self.project.project_description = step['summary']
            self.project.project_description_messages = step['messages']
            return

        # PROJECT DESCRIPTION
        if 'app_type' not in self.project.args:
            self.project.args['app_type'] = ask_for_app_type()
        if 'name' not in self.project.args:
            self.project.args['name'] = clean_filename(ask_user(self.project, 'What is the project name?'))

        self.project.root_path = setup_workspace(self.project.args)

        self.project.app = save_app(self.project)

        main_prompt = ask_for_main_app_definition(self.project)

        print(json.dumps({'open_project': {
            #'uri': 'file:///' + self.project.root_path.replace('\\', '/'),
            'path': self.project.root_path,
            'name': self.project.args['name'],
        }}), type='info')

        high_level_messages = get_additional_info_from_openai(
            self.project,
            generate_messages_from_description(main_prompt, self.project.args['app_type'], self.project.args['name']))

        print(green_bold('Project Summary:\n'))
        convo_project_description = AgentConvo(self)
        high_level_summary = convo_project_description.send_message('utils/summary.prompt',
                                                                    {'conversation': '\n'.join(
                                                                        [f"{msg['role']}: {msg['content']}" for msg in
                                                                         high_level_messages])})

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "prompt": main_prompt,
            "messages": high_level_messages,
            "summary": high_level_summary,
            "app_data": generate_app_data(self.project.args)
        })

        self.project.project_description = high_level_summary
        self.project.project_description_messages = high_level_messages
        return
        # PROJECT DESCRIPTION END

    def get_user_stories(self):
        self.project.current_step = USER_STORIES_STEP
        self.convo_user_stories = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], USER_STORIES_STEP)
        if step and not should_execute_step(self.project.args['step'], USER_STORIES_STEP):
            step_already_finished(self.project.args, step)
            self.convo_user_stories.messages = step['messages']
            return step['user_stories']

        # USER STORIES
        msg = f"User Stories:\n"
        print(green_bold(msg))
        logger.info(msg)

        self.project.user_stories = self.convo_user_stories.continuous_conversation('user_stories/specs.prompt', {
            'name': self.project.args['name'],
            'prompt': self.project.project_description,
            'clarifications': self.project.project_description_messages,
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
        self.project.current_step = USER_TASKS_STEP
        self.convo_user_stories.high_level_step = self.project.current_step

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], USER_TASKS_STEP)
        if step and not should_execute_step(self.project.args['step'], USER_TASKS_STEP):
            step_already_finished(self.project.args, step)
            return step['user_tasks']

        # USER TASKS
        msg = f"User Tasks:\n"
        print(green_bold(msg))
        logger.info(msg)

        self.project.user_tasks = self.convo_user_stories.continuous_conversation('user_stories/user_tasks.prompt',
                                                                                  {'END_RESPONSE': END_RESPONSE})

        logger.info(f"Final user tasks: {self.project.user_tasks}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_tasks": self.project.user_tasks,
            "app_data": generate_app_data(self.project.args)
        })

        return self.project.user_tasks
        # USER TASKS END
