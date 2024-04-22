import json
import os

from utils.utils import step_already_finished
from helpers.Agent import Agent
from utils.style import color_green_bold
from helpers.AgentConvo import AgentConvo

from utils.utils import should_execute_step, generate_app_data
from database.database import save_progress, get_progress_steps, save_feature, edit_development_plan, edit_feature_plan
from logger.logger import logger
from const.function_calls import DEVELOPMENT_PLAN, UPDATE_DEVELOPMENT_PLAN
from const.common import EXAMPLE_PROJECT_PLAN
from templates import apply_project_template

DEVELOPMENT_PLANNING_STEP = 'development_planning'


class TechLead(Agent):
    def __init__(self, project):
        super().__init__('tech_lead', project)
        self.save_dev_steps = False
        self.convo_feature_plan = AgentConvo(self)

    def create_development_plan(self):
        self.project.current_step = DEVELOPMENT_PLANNING_STEP
        self.convo_development_plan = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], DEVELOPMENT_PLANNING_STEP)
        if step and not should_execute_step(self.project.args['step'], DEVELOPMENT_PLANNING_STEP):
            step_already_finished(self.project.args, step)
            self.project.development_plan = step['development_plan']
            return

        existing_summary = apply_project_template(self.project)

        # DEVELOPMENT PLANNING
        print(color_green_bold("Starting to create the action plan for development...\n"), category='agent:tech-lead')
        logger.info("Starting to create the action plan for development...")

        if self.project.project_manager.is_example_project:
            llm_response = {"plan": EXAMPLE_PROJECT_PLAN}
        else:
            llm_response = self.convo_development_plan.send_message('development/plan.prompt',
                {
                    "name": self.project.args['name'],
                    "app_type": self.project.args['app_type'],
                    "app_summary": self.project.project_description,
                    "user_stories": self.project.user_stories,
                    "user_tasks": self.project.user_tasks,
                    "architecture": self.project.architecture,
                    "technologies": self.project.system_dependencies + self.project.package_dependencies,
                    "existing_summary": existing_summary,
                    "files": self.project.get_all_coded_files(),
                    "task_type": 'app',
                    "is_complex_app": self.project.is_complex_app,
                }, DEVELOPMENT_PLAN)
        self.project.development_plan = llm_response['plan']

        logger.info('Plan for development is created.')

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "development_plan": self.project.development_plan, "app_data": generate_app_data(self.project.args)
        })

        return

    def create_feature_plan(self, feature_description):
        self.save_dev_steps = True
        self.convo_feature_plan = AgentConvo(self)

        llm_response = self.convo_feature_plan.send_message('development/feature_plan.prompt',
            {
                "name": self.project.args['name'],
                "app_type": self.project.args['app_type'],
                "app_summary": self.project.project_description,
                "user_stories": self.project.user_stories,
                "user_tasks": self.project.user_tasks,
                "architecture": self.project.architecture,
                "technologies": self.project.system_dependencies + self.project.package_dependencies,
                "directory_tree": self.project.get_directory_tree(True),
                "files": self.project.get_all_coded_files(),
                "previous_features": self.project.previous_features,
                "feature_description": feature_description,
                "task_type": 'feature',
            }, DEVELOPMENT_PLAN)

        self.project.development_plan = llm_response['plan']

        logger.info('Plan for feature development is created.')
        return

    def create_feature_summary(self, feature_description):
        self.save_dev_steps = True
        self.convo_feature_summary = AgentConvo(self)

        llm_response = self.convo_feature_summary.send_message('development/feature_summary.prompt',
            {
                "name": self.project.args['name'],
                "app_type": self.project.args['app_type'],
                "app_summary": self.project.project_description,
                "feature_description": feature_description,
                "development_tasks": self.project.development_plan,
            })

        self.project.feature_summary = llm_response

        if not self.project.skip_steps:
            save_feature(self.project.args['app_id'],
                         self.project.feature_summary,
                         self.convo_feature_plan.messages,
                         self.project.checkpoints['last_development_step']['id'])

        logger.info('Summary for new feature is created.')
        return

    def update_plan(self, task_source, llm_solutions, modified_files, i):
        """
        Update the development plan after a task is finished.

        :param task_source: The source of the task, one of: 'app', 'feature'.
        :param llm_solutions: The LLM solutions (iterations) for the last finished task.
        :param modified_files: The files that were modified during the last task.
        :param i: The index of the last finished task in the development plan.

        :return: True if the task was successfully updated, False otherwise.
        """
        self.save_dev_steps = True
        print('Updating development plan...', category='agent:tech-lead')
        finished_tasks = [task for task in self.project.development_plan if task.get('finished', False)]
        not_finished_tasks = [task for task in self.project.development_plan if not task.get('finished', False)]
        files = [
            file_dict for file_dict in self.project.get_all_coded_files()
            if any(os.path.normpath(file_dict['full_path']).endswith(os.path.normpath(modified_file.lstrip('.'))) for
                   modified_file in modified_files)
        ]
        update_task_convo = AgentConvo(self, temperature=0)
        llm_response = update_task_convo.send_message('development/update_plan.prompt', {
            "name": self.project.args['name'],
            "app_type": self.project.args['app_type'],
            "app_summary": self.project.project_description,
            "finished_tasks": finished_tasks,
            "not_finished_tasks": not_finished_tasks,
            "last_finished_task": self.project.development_plan[i],
            "task_source": task_source,
            "llm_solutions": llm_solutions,
            "files": files,
        }, UPDATE_DEVELOPMENT_PLAN)

        finished_tasks[-1]['description'] = llm_response['updated_current_task']['description']
        self.project.development_plan = finished_tasks + llm_response['plan']
        if task_source == 'app':
            db_task_update = edit_development_plan(self.project.args['app_id'], {'development_plan': self.project.development_plan})
        else:
            db_task_update = edit_feature_plan(self.project.args['app_id'], {'llm_response': {'text': json.dumps({'plan': self.project.development_plan})}})

        if db_task_update:
            print('Successfully updated development plan.')
        else:
            print('Failed to update development plan.')

        return db_task_update
