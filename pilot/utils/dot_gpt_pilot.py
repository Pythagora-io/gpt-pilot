import json
import os
import yaml
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

USE_GPTPILOT_FOLDER = os.getenv('USE_GPTPILOT_FOLDER') == 'true'


# TODO: Parse files from the `.gpt-pilot` directory to resume a project - `user_stories` may have changed - include checksums for sections which may need to be reprocessed.
# TODO: Save a summary at the end of each task/sprint.
class DotGptPilot:
    """
    Manages the `.gpt-pilot` directory.
    """
    def __init__(self, log_chat_completions: bool = True):
        if not USE_GPTPILOT_FOLDER:
            return
        self.log_chat_completions = log_chat_completions
        self.dot_gpt_pilot_path = self.with_root_path('~', create=False)
        self.chat_log_path = self.chat_log_folder(None)

    def with_root_path(self, root_path: str, create=True):
        if not USE_GPTPILOT_FOLDER:
            return
        dot_gpt_pilot_path = os.path.expanduser(os.path.join(root_path, '.gpt-pilot'))
        self.dot_gpt_pilot_path = dot_gpt_pilot_path

        # Create the `.gpt-pilot` directory if required.
        if create and self.log_chat_completions:  # (... or ...):
            self.chat_log_folder(None)

        return dot_gpt_pilot_path

    def chat_log_folder(self, task):
        if not USE_GPTPILOT_FOLDER:
            return
        chat_log_path = os.path.join(self.dot_gpt_pilot_path, 'chat_log')
        if task is not None:
            chat_log_path = os.path.join(chat_log_path, 'task_' + str(task))

        os.makedirs(chat_log_path, exist_ok=True)
        self.chat_log_path = chat_log_path
        return chat_log_path

    def log_chat_completion(self, endpoint: str, model: str, req_type: str, messages: list[dict], response: str):
        if not USE_GPTPILOT_FOLDER:
            return
        if self.log_chat_completions:
            time = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
            with open(os.path.join(self.chat_log_path, f'{time}-{req_type}.yaml'), 'w', encoding="utf-8") as file:
                data = {
                    'endpoint': endpoint,
                    'model': model,
                    'messages': messages,
                    'response': response,
                }

                yaml.safe_dump(data, file, width=120, indent=2, default_flow_style=False, sort_keys=False)

    def log_chat_completion_json(self, endpoint: str, model: str, req_type: str, functions: dict, json_response: str):
        if not USE_GPTPILOT_FOLDER:
            return
        if self.log_chat_completions:
            time = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')

            with open(os.path.join(self.chat_log_path, f'{time}-{req_type}.json'), 'w', encoding="utf-8") as file:
                data = {
                    'endpoint': endpoint,
                    'model': model,
                    'functions': functions,
                    'response': json.loads(json_response),
                }

                json.dump(data, file, indent=2)

    def write_project(self, project):
        if not USE_GPTPILOT_FOLDER:
            return
        data = {
            'name': project.args['name'],
            'description': project.project_description,
            'user_stories': project.user_stories,
            'architecture': project.architecture,
            'system_dependencies': project.system_dependencies,
            'development_plan': project.development_plan,
        }

        with open(os.path.join(self.dot_gpt_pilot_path, 'project.yaml'), 'w') as file:
            yaml.safe_dump(data, file, width=120, indent=2, default_flow_style=False, sort_keys=False)
