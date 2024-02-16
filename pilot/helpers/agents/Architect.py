from utils.utils import step_already_finished
from helpers.Agent import Agent
import json

from utils.style import color_green_bold, color_yellow_bold
from const.function_calls import ARCHITECTURE
import platform

from utils.utils import should_execute_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from helpers.AgentConvo import AgentConvo
from prompts.prompts import ask_user
from templates import PROJECT_TEMPLATES

ARCHITECTURE_STEP = 'architecture'
WARN_SYSTEM_DEPS = ["docker", "kubernetes", "microservices"]
WARN_FRAMEWORKS = ["react", "react.js", "next.js", "vue", "vue.js", "svelte", "angular"]
WARN_FRAMEWORKS_URL = "https://github.com/Pythagora-io/gpt-pilot/wiki/Using-GPT-Pilot-with-frontend-frameworks"


class Architect(Agent):
    def __init__(self, project):
        super().__init__('architect', project)
        self.convo_architecture = None

    def get_architecture(self):
        print(json.dumps({
            "project_stage": "architecture"
        }), type='info')

        self.project.current_step = ARCHITECTURE_STEP

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], ARCHITECTURE_STEP)
        if step and not should_execute_step(self.project.args['step'], ARCHITECTURE_STEP):
            step_already_finished(self.project.args, step)
            self.project.architecture = None
            self.project.system_dependencies = None
            self.project.package_dependencies = None
            self.project.project_template = None
            db_data = step["architecture"]
            if db_data:
                if isinstance(db_data, dict):
                    self.project.architecture = db_data["architecture"]
                    self.project.system_dependencies = db_data["system_dependencies"]
                    self.project.package_dependencies = db_data["package_dependencies"]
                    self.project.project_template = db_data.get("project_template")
                elif isinstance(db_data, list):
                    self.project.architecture = ""
                    self.project.system_dependencies = [
                        {
                            "name": dep,
                            "description": "",
                            "test": "",
                            "required_locally": False
                        } for dep in db_data
                    ]
                    self.project.package_dependencies = []
                    self.project.project_template = None
            return

        print(color_green_bold("Planning project architecture...\n"))
        logger.info("Planning project architecture...")

        self.convo_architecture = AgentConvo(self)
        llm_response = self.convo_architecture.send_message('architecture/technologies.prompt',
            {'name': self.project.args['name'],
             'app_summary': self.project.project_description,
             'user_stories': self.project.user_stories,
             'user_tasks': self.project.user_tasks,
             "os": platform.system(),
             'app_type': self.project.args['app_type'],
             "templates": PROJECT_TEMPLATES,
            },
            ARCHITECTURE
        )

        self.project.architecture = llm_response["architecture"]
        self.project.system_dependencies = llm_response["system_dependencies"]
        self.project.package_dependencies = llm_response["package_dependencies"]
        self.project.project_template = llm_response["template"]

        warn_system_deps = [dep["name"] for dep in self.project.system_dependencies if dep["name"].lower() in WARN_SYSTEM_DEPS]
        warn_package_deps = [dep["name"] for dep in self.project.package_dependencies if dep["name"].lower() in WARN_FRAMEWORKS]

        if warn_system_deps:
            print(color_yellow_bold(
                f"Warning: GPT Pilot doesn't officially support {', '.join(warn_system_deps)}. "
                f"You can try to use {'it' if len(warn_system_deps) == 1 else 'them'}, but you may run into problems."
            ))
            print('continue', type='buttons-only')
            ask_user(self.project, "Press ENTER if you still want to proceed. If you'd like to modify the project description, close the app and start a new one.", require_some_input=False)

        if warn_package_deps:
            print(color_yellow_bold(
                f"Warning: GPT Pilot works best with vanilla JavaScript. "
                f"You can try try to use {', '.join(warn_package_deps)}, but you may run into problems. "
                f"Visit {WARN_FRAMEWORKS_URL} for more information."
            ))
            print('continue', type='buttons-only')
            ask_user(self.project, "Press ENTER if you still want to proceed. If you'd like to modify the project description, close the app and start a new one.", require_some_input=False)

        logger.info(f"Final architecture: {self.project.architecture}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_architecture.messages,
            "architecture": llm_response,
            "app_data": generate_app_data(self.project.args)
        })

        return
