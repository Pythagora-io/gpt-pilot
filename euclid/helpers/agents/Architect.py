from utils.utils import step_already_finished
from helpers.Agent import Agent
import json
from termcolor import colored
from const.function_calls import ARCHITECTURE

from utils.utils import execute_step, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user
from helpers.AgentConvo import AgentConvo

class Architect(Agent):
    def __init__(self, project):
        super().__init__('architect', project)

    def get_architecture(self):
        self.project.current_step = 'architecture'
        self.convo_architecture = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return step['architecture']

        # ARCHITECTURE
        print(colored(f"Planning project architecture...\n", "green"))
        logger.info(f"Planning project architecture...")

        architecture = self.convo_architecture.send_message('architecture/technologies.prompt',
            {'prompt': self.project.high_level_summary,
            'user_stories': self.project.user_stories,
            'user_tasks': self.project.user_tasks,
            'app_type': self.project.args['app_type']}, ARCHITECTURE)

        architecture = get_additional_info_from_user(architecture, 'architect')

        logger.info(f"Final architecture: {architecture}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_architecture.messages,
            "architecture": architecture,
            "app_data": generate_app_data(self.project.args)
        })

        return architecture
        # ARCHITECTURE END
