import os


class Agent:
    
    model: str;

    def __init__(self, role: str, project):
        self.role = role
        self.project = project
        self.model = os.getenv('DEFAULT_MODEL_NAME', 'gpt-4-turbo-preview');

        agentModelName = f'{role.upper()}_MODEL_NAME';
        if agentModelName in os.environ:
            self.model = os.getenv(agentModelName, 'gpt-4-turbo-preview');

        


        