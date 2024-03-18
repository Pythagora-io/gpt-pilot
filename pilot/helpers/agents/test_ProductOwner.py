from unittest.mock import MagicMock
from dotenv import load_dotenv
from helpers.agents import ProductOwner

load_dotenv()


class TestProductOwner:
    def test_product_owner_model_override(self, monkeypatch):
        # Given any project
        project = MagicMock()

        model = 'some_model'
        monkeypatch.setenv('PRODUCT_OWNER_MODEL_NAME', model)

        # and a developer who will execute any task
        agent = ProductOwner(project)
        assert agent.model == model