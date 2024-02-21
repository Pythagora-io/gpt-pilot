import json
from utils.style import color_green_bold
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from logger.logger import logger
from database.database import get_app, save_progress, save_app, get_progress_steps
from utils.utils import should_execute_step, generate_app_data, step_already_finished, clean_filename
from utils.files import setup_workspace
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, ask_user
from const.llm import END_RESPONSE
from const.messages import MAX_PROJECT_NAME_LENGTH
from const.common import EXAMPLE_PROJECT_DESCRIPTION

PROJECT_DESCRIPTION_STEP = 'project_description'
USER_STORIES_STEP = 'user_stories'
USER_TASKS_STEP = 'user_tasks'


class ProductOwner(Agent):
    def __init__(self, project):
        super().__init__('product_owner', project)

    def get_project_description(self, spec_writer):
        print(json.dumps({
            "project_stage": "project_description"
        }), type='info')

        self.project.app = get_app(self.project.args['app_id'], error_if_not_found=False)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        if self.project.app is not None:
            step = get_progress_steps(self.project.args['app_id'], PROJECT_DESCRIPTION_STEP)
            if step and not should_execute_step(self.project.args['step'], PROJECT_DESCRIPTION_STEP):
                step_already_finished(self.project.args, step)
                self.project.set_root_path(setup_workspace(self.project.args))
                self.project.project_description = step['summary']
                self.project.project_description_messages = step['messages']
                self.project.main_prompt = step['prompt']
                return

        # PROJECT DESCRIPTION
        self.project.current_step = PROJECT_DESCRIPTION_STEP
        is_example_project = False

        if 'app_type' not in self.project.args:
            self.project.args['app_type'] = ask_for_app_type()
        if 'name' not in self.project.args:
            while True:
                question = 'What is the project name?'
                print(question, type='ipc')
                print('start an example project', type='button')
                project_name = ask_user(self.project, question)
                if len(project_name) <= MAX_PROJECT_NAME_LENGTH:
                    break
                else:
                    print(f"Hold your horses cowboy! Please, give project NAME with max {MAX_PROJECT_NAME_LENGTH} characters.")

            if project_name.lower() == 'start an example project':
                is_example_project = True
                project_name = 'Example Project'

            self.project.args['name'] = clean_filename(project_name)

        self.project.app = save_app(self.project)

        self.project.set_root_path(setup_workspace(self.project.args))

        if is_example_project:
            print(EXAMPLE_PROJECT_DESCRIPTION)
            self.project.main_prompt = EXAMPLE_PROJECT_DESCRIPTION
        else:
            print(color_green_bold(
                "GPT Pilot currently works best for web app projects using Node, Express and MongoDB. "
                "You can use it with other technologies, but you may run into problems "
                "(eg. React might not work as expected).\n"
            ))
            self.project.main_prompt = ask_for_main_app_definition(self.project)

        print(json.dumps({'open_project': {
            #'uri': 'file:///' + self.project.root_path.replace('\\', '/'),
            'path': self.project.root_path,
            'name': self.project.args['name'],
        }}), type='info')

        high_level_messages = []
        high_level_summary = spec_writer.create_spec(self.project.main_prompt)

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "prompt": self.project.main_prompt,
            "messages": high_level_messages,
            "summary": high_level_summary,
            "app_data": generate_app_data(self.project.args)
        })

        self.project.project_description = high_level_summary
        self.project.project_description_messages = high_level_messages
        return
        # PROJECT DESCRIPTION END

    def get_user_stories(self):
        if not self.project.args.get('advanced', False):
            return

        print(json.dumps({
            "project_stage": "user_stories"
        }), type='info')

        self.project.current_step = USER_STORIES_STEP
        self.convo_user_stories = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], USER_STORIES_STEP)
        if step and not should_execute_step(self.project.args['step'], USER_STORIES_STEP):
            step_already_finished(self.project.args, step)
            self.convo_user_stories.messages = step['messages']
            self.project.user_stories = step['user_stories']
            return

        # USER STORIES
        msg = "User Stories:\n"
        print(color_green_bold(msg))
        logger.info(msg)

        self.project.user_stories = self.convo_user_stories.continuous_conversation('user_stories/specs.prompt', {
            'name': self.project.args['name'],
            'prompt': self.project.project_description,
            'app_type': self.project.args['app_type'],
            'END_RESPONSE': END_RESPONSE
        })

        logger.info(f"Final user stories: {self.project.user_stories}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_user_stories.messages,
            "user_stories": self.project.user_stories,
            "app_data": generate_app_data(self.project.args)
        })

        return
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
        msg = "User Tasks:\n"
        print(color_green_bold(msg))
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
