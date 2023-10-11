import os
import yaml
from datetime import datetime


# TODO: Parse files from the `.gpt-pilot` directory to resume a project - `user_stories` may have changed - include checksums for sections which may need to be reprocessed.
# TODO: Save a summary at the end of each task/sprint.
class DotGptPilot:
    """
    Manages the `.gpt-pilot` directory.
    """
    def __init__(self, log_chat_completions: bool = True):
        self.log_chat_completions = log_chat_completions
        self.dot_gpt_pilot_path = self.with_root_path('~', create=False)

    def with_root_path(self, root_path: str, create=True):
        print(f'--------------------with_root_path: {root_path}, create: {create}')
        dot_gpt_pilot_path = os.path.join(root_path, '.gpt-pilot')

        # Create the `.gpt-pilot` directory if required.
        print(f'create and self.log_chat_completions: {create}, {self.log_chat_completions}')
        if create and self.log_chat_completions:  # (... or ...):
            print('creating dirs: ' + os.path.join(dot_gpt_pilot_path, 'chat_log'))
            os.makedirs(os.path.join(dot_gpt_pilot_path, 'chat_log'), exist_ok=True)
        else:
            print('not creating dirs')

        self.dot_gpt_pilot_path = dot_gpt_pilot_path
        return dot_gpt_pilot_path

    def log_chat_completion(self, endpoint: str, model: str, req_type: str, messages: list[dict], response: str):
        if self.log_chat_completions:
            time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            with open(os.path.join(self.dot_gpt_pilot_path, 'chat_log', f'{time}-{req_type}.yaml'), 'w') as file:
                data = {
                    'endpoint': endpoint,
                    'model': model,
                    'messages': messages,
                    'response': response,
                }

                yaml.safe_dump(data, file, width=120, indent=2, default_flow_style=False, sort_keys=False)

    def write_project(self, project):
        data = {
            'name': project.args['name'],
            'description': project.project_description,
            'user_stories': project.user_stories,
            'architecture': project.architecture,
            'development_plan': project.development_plan,
        }

        with open(os.path.join(self.dot_gpt_pilot_path, 'project.yaml'), 'w') as file:
            yaml.safe_dump(data, file, width=120, indent=2, default_flow_style=False, sort_keys=False)
