from dotenv import load_dotenv
from helpers.agents.Developer import Developer
from helpers.AgentConvo import AgentConvo
from .test_Project import create_project

load_dotenv()

from database.database import database

# database.init()
# database.connect(reuse_if_open=True)


def test_send_message_saved_dev_step(monkeypatch):
    # Given
    # monkeypatch.setenv('ENDPOINT', endpoint)
    project = create_project()
    project.args['app_id'] = '6f5f0a31-3c70-4162-86ff-3fa938aca9b9'
    project.checkpoints['last_development_step'] = 135
    project.current_step = 'coding'
    developer = Developer(project)
    convo = AgentConvo(developer)

    # When
    response = convo.send_message('development/define_user_review_goal.prompt', {'os': 'Test'})

    # Then
    assert response is not None
