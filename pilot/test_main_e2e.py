import os
import builtins
import pytest
from unittest.mock import patch
from dotenv import load_dotenv
load_dotenv()

from database.database import create_tables
from helpers.Project import Project
from test.mock_questionary import MockQuestionary
from .main import init, get_custom_print


@pytest.mark.xfail(reason="Reliably fails on CI, reliably works locally")
@patch.dict(os.environ, {"DB_NAME": ":memory:"})
def test_init():
    # When
    args = init()

    # Then
    for field in ['app_id', 'user_id', 'email']:
        assert args[field] is not None

    for field in ['workspace', 'step']:
        assert args[field] is None


@pytest.mark.slow
@pytest.mark.uses_tokens
@pytest.mark.skip(reason="Uses lots of tokens")
@pytest.mark.parametrize("endpoint, model", [
    ("OPENAI", "gpt-4"),
    ("OPENROUTER", "openai/gpt-3.5-turbo"),
    ("OPENROUTER", "meta-llama/codellama-34b-instruct"),
    ("OPENROUTER", "google/palm-2-chat-bison"),
    ("OPENROUTER", "google/palm-2-codechat-bison"),
    # TODO: See https://github.com/1rgs/jsonformer-claude/blob/main/jsonformer_claude/main.py
    #           https://github.com/guidance-ai/guidance - token healing
    ("OPENROUTER", "anthropic/claude-2"),
])
def test_end_to_end(endpoint, model, monkeypatch):
    # Given
    monkeypatch.setenv('ENDPOINT', endpoint)
    monkeypatch.setenv('MODEL_NAME', model)

    create_tables()
    args = init()
    builtins.print, ipc_client_instance = get_custom_print(args)
    project = Project(args)
    mock_questionary = MockQuestionary([
        'Test App',
        'A web-based chat app',
        # 5 clarifying questions
        'Users can send direct messages to each other but with no group chat functionality',
        'No authentication is required at this stage',
        'Use your best judgement',
        'Use your best judgement',
        'Use your best judgement',
    ])

    # When
    with patch('utils.questionary.questionary', mock_questionary):
        project.start()
