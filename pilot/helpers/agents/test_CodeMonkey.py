import builtins
import os
from unittest.mock import patch
from dotenv import load_dotenv
from pilot.helpers.agents import Architect, CodeMonkey

from pilot.helpers.test_Project import create_project
load_dotenv()

from main import get_custom_print


class TestTechLead:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

        name = 'TestCodeMonkey'
        self.project = create_project()
        self.project.app_id = 'test-code-monkey'
        self.project.name = name


        self.project.set_root_path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/TestCodeMonkey')))

    def test_code_monkey_model_override(self, monkeypatch):
        # Given any project
        project = create_project()

        model = 'some_model'
        monkeypatch.setenv('CODE_MONKEY_MODEL_NAME', model)

        # and a developer who will execute any task
        agent = CodeMonkey(project)
        assert agent.model == model