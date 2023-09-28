from utils.utils import step_already_finished
from helpers.Agent import Agent
import json
from utils.style import green_bold
from const.function_calls import ARCHITECTURE

from utils.utils import should_execute_step, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user
from helpers.AgentConvo import AgentConvo

ARCHITECTURE_STEP = 'architecture'


class Architect(Agent):
    def __init__(self, project):
        super().__init__('architect', project)
        self.convo_architecture = None

    def get_architecture(self):
        self.project.current_step = ARCHITECTURE_STEP

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], ARCHITECTURE_STEP)
        if step and not should_execute_step(self.project.args['step'], ARCHITECTURE_STEP):
            step_already_finished(self.project.args, step)
            return step['architecture']

        # ARCHITECTURE
        print(green_bold(f"Planning project architecture...\n"))
        logger.info(f"Planning project architecture...")

        self.convo_architecture = AgentConvo(self)
        architecture = self.convo_architecture.send_message('architecture/technologies.prompt',
            {'name': self.project.args['name'],
             'prompt': self.project.project_description,
             'user_stories': self.project.user_stories,
            #  'user_tasks': self.project.user_tasks,
             'app_type': self.project.args['app_type']}, ARCHITECTURE)

        # TODO: Project.args should be a defined class so that all of the possible args are more obvious
        if self.project.args.get('advanced', False):
            architecture = get_additional_info_from_user(self.project, architecture, 'architect')

        logger.info(f"Final architecture: {architecture}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_architecture.messages,
            "architecture": architecture,
            "app_data": generate_app_data(self.project.args)
        })

        return architecture
        # ARCHITECTURE END
