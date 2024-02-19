import builtins
import os
from unittest.mock import patch
from dotenv import load_dotenv
from helpers.agents import ProductOwner

from helpers.test_Project import create_project
load_dotenv()

from main import get_custom_print


class TestProductOwner:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

        name = 'TestProductOwner'
        self.project = create_project()
        self.project.app_id = 'test-product-owner'
        self.project.name = name


        self.project.set_root_path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/TestProductOwner')))

    def test_product_owner_model_override(self, monkeypatch):
        # Given any project
        project = create_project()

        model = 'some_model'
        monkeypatch.setenv('PRODUCT_OWNER_MODEL_NAME', model)

        # and a developer who will execute any task
        agent = ProductOwner(project)
        assert agent.model == model