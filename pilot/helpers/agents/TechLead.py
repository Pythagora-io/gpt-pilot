from utils.utils import step_already_finished
from helpers.Agent import Agent
import json
from termcolor import colored
from const.function_calls import DEV_STEPS
from helpers.cli import build_directory_tree
from helpers.AgentConvo import AgentConvo

from utils.utils import execute_step, array_of_objects_to_string, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from const.function_calls import FILTER_OS_TECHNOLOGIES, DEVELOPMENT_PLAN, EXECUTE_COMMANDS
from const.code_execution import MAX_COMMAND_DEBUG_TRIES
from utils.utils import get_os_info
from helpers.cli import execute_command

class TechLead(Agent):
    def __init__(self, project):
        super().__init__('tech_lead', project)

    def create_development_plan(self):
        self.project.current_step = 'development_planning'
        self.convo_development_plan = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return step['development_plan']
        
        # DEVELOPMENT PLANNING
        print(colored(f"Starting to create the action plan for development...\n", "green", attrs=['bold']))
        logger.info(f"Starting to create the action plan for development...")

        # TODO add clarifications
        self.development_plan = self.convo_development_plan.send_message('development/plan.prompt',
            {
                "name": self.project.args['name'],
                "app_type": self.project.args['app_type'],
                "app_summary": self.project.project_description,
                "clarification": [],
                "user_stories": self.project.user_stories,
                # "user_tasks": self.project.user_tasks,
                "technologies": self.project.architecture
            }, DEVELOPMENT_PLAN)

        logger.info('Plan for development is created.')

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "development_plan": self.development_plan, "app_data": generate_app_data(self.project.args)
        })

        return self.development_plan