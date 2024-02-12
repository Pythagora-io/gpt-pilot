import os

from helpers import Project


class Agent:
    
    modle: str;
    project: Project;

    def __init__(self, role: str, project: Project):
        self.role = role
        self.project = project
        self.modle = os.getenv('DEFAULT_MODEL_NAME', 'gpt-4-turbo-preview');

        agentModelName = f'{role.upper()}_MODEL_NAME';
        if agentModelName in os.environ:
            self.modle = os.getenv(agentModelName, 'gpt-4-turbo-preview');

        


        