from unittest.mock import MagicMock
from dotenv import load_dotenv
from pilot.helpers.agents import TechnicalWriter
load_dotenv()


class TestTechLead:
    def test_technical_writer_model_override(self, monkeypatch):
        # Given any project
        project = MagicMock()

        model = 'some_model'
        monkeypatch.setenv('TECHNICAL_WRITER_MODEL_NAME', model)

        # and a developer who will execute any task
        agent = TechnicalWriter(project)
        assert agent.model == model