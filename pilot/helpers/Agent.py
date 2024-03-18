import os

from const.common import DEFAULT_MODEL_NAME


class Agent:
    model: str
    
    def __init__(self, role, project):
        self.role = role
        self.project = project
        self.model = os.getenv('DEFAULT_MODEL_NAME', 'gpt-4-turbo-preview')

        agentModelName = f'{role.upper()}_MODEL_NAME'
        if agentModelName in os.environ:
            self.model = os.getenv(agentModelName, DEFAULT_MODEL_NAME)