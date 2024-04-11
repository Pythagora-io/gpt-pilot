import os

from const.common import DEFAULT_MODEL_NAME


class Agent:
    model: str
    
    def __init__(self, role, project):
        self.role = role
        self.project = project
        self.model = os.getenv('MODEL_NAME', DEFAULT_MODEL_NAME)

        agentModelName = f'{role.upper()}_MODEL_NAME'
        if agentModelName in os.environ:
            self.model = os.getenv(agentModelName)