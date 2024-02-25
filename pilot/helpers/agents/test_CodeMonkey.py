from unittest.mock import MagicMock
from dotenv import load_dotenv
from pilot.helpers.agents import CodeMonkey

load_dotenv()

from main import get_custom_print


class TestTechLead:
    def test_code_monkey_model_override(self, monkeypatch):
        # Given any project
        project = MagicMock()
        model = 'some_model'
        monkeypatch.setenv('CODE_MONKEY_MODEL_NAME', model)

        # and a developer who will execute any task
        agent = CodeMonkey(project)
        assert agent.model == model