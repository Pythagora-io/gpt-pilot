from unittest.mock import MagicMock
from dotenv import load_dotenv
from pilot.helpers.agents import Architect

load_dotenv()


class TestTechLead:

    def test_architect_model_override(self, monkeypatch):
        # Given any project
        project = MagicMock()

        model = 'some_model'
        monkeypatch.setenv('ARCHITECT_MODEL_NAME', model)

        # and a developer who will execute any task
        agent = Architect(project)
        assert agent.model == model