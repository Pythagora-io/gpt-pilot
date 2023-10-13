import os
from helpers.agents import Developer, ENVIRONMENT_SETUP_STEP
from helpers import AgentConvo, Project
from helpers.files import update_file
from database import save_app


def run_command_until_success():
    name = 'run_command_until_success'
    project = Project({
        'app_id': '84c2c532-e07c-4694-bcb0-70767c348b07',
        'name': name,
        'app_type': '',
        'user_id': '97510ce7-dbca-44b6-973c-d27346ce4009',
        'email': '7ed2f578-c791-4719-959c-dedf94394ad3',
        'password': 'secret',
    },
        name=name,
        architecture=[],
        user_stories=[]
    )

    project.set_root_path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     '../../../workspace/TestDeveloper')))
    project.technologies = []
    project.current_step = ENVIRONMENT_SETUP_STEP
    project.app = save_app(project)

    update_file(f'{project.root_path}/package.json',
                '{"dependencies": {"axios": "^1.5.0", "express": "^4.18.2", "mongoose": "^7.5.0"}}')

    developer = Developer(project)
    developer.run_command = 'npm install'

    convo = AgentConvo(developer)
    step = {
        'type': 'human_intervention',
        'human_intervention_description': 'I want you to test that this process works from the CLI _and_ from the UI.',
    }

    developer.step_human_intervention(convo, step)
