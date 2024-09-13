import codecs
import json
from os.path import dirname, join

import pytest
from pydantic import ValidationError

from core.config import Config, ConfigLoader, LLMProvider, get_config, loader

test_config_data = {
    "llm": {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-openai",
            "connect_timeout": 60.0,
            "read_timeout": 10.0,
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com",
            "api_key": "sk-anthropic",
            "connect_timeout": 60.0,
            "read_timeout": 10.0,
        },
    },
    "agent": {
        "default": {
            "provider": "openai",
            "model": "gpt-4-turbo",
            "temperature": 0.1,
        },
        "CodeMonkey": {
            "provider": "anthropic",
            "model": "claude-3-opus",
            "temperature": 0.5,
        },
    },
}


def test_parse_config():
    config = ConfigLoader.from_json(json.dumps(test_config_data))

    assert config.llm_for_agent().provider == LLMProvider.OPENAI
    assert config.llm_for_agent().model == "gpt-4-turbo"
    assert config.llm_for_agent().base_url == "https://api.openai.com/v1"
    assert config.llm_for_agent().api_key == "sk-openai"
    assert config.llm_for_agent("CodeMonkey").provider == LLMProvider.ANTHROPIC
    assert config.llm_for_agent("CodeMonkey").model == "claude-3-opus"
    assert config.llm_for_agent("CodeMonkey").base_url == "https://api.anthropic.com"
    assert config.llm_for_agent("CodeMonkey").api_key == "sk-anthropic"


def test_default_agent_llm_config():
    data = {
        "llm": {"openai": test_config_data["llm"]["openai"]},
        "agent": {"default": test_config_data["agent"]["default"]},
    }

    config = ConfigLoader.from_json(json.dumps(data))

    assert config.llm_for_agent("CodeMonkey").provider == LLMProvider.OPENAI


def test_builtin_defaults():
    config = ConfigLoader.from_json("{}")

    assert config.llm_for_agent().provider == LLMProvider.OPENAI
    assert config.llm_for_agent().model == "gpt-4o-2024-05-13"
    assert config.llm_for_agent().base_url is None
    assert config.llm_for_agent().api_key is None


def test_unsupported_provider():
    data = {
        "llm": {
            "default": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-openai",
            }
        },
        "agent": {
            "default": {
                "provider": "acme",
                "model": "gpt-4-turbo",
                "temperature": 0.1,
            }
        },
    }

    with pytest.raises(ValidationError) as einfo:
        ConfigLoader.from_json(json.dumps(data))

    assert "llm.default.[key]" in str(einfo.value)
    assert "agent.default.provider" in str(einfo.value)


def test_load_from_file_with_comments():
    config_path = join(dirname(__file__), "testconfig.json")

    config = ConfigLoader().load(config_path)
    assert config.llm_for_agent("CodeMonkey").provider == LLMProvider.ANTHROPIC


def test_default_config():
    loader.config = Config()
    config = get_config()
    assert config.llm_for_agent().provider == LLMProvider.OPENAI
    assert config.log.level == "DEBUG"


@pytest.mark.parametrize(
    ("encoding", "bom"),
    [
        ("utf-8", None),
        ("utf-16", None),
        ("utf-16-le", codecs.BOM_UTF16_LE),
        ("utf-16-be", codecs.BOM_UTF16_BE),
    ],
)
def test_encodings(encoding, bom, tmp_path):
    config_json = json.dumps(test_config_data)
    config_path = tmp_path / "config.json"

    with open(config_path, "wb") as f:
        if bom:
            f.write(bom)
        f.write(config_json.encode(encoding))

    config = ConfigLoader().load(config_path)
    assert config.llm_for_agent().model == "gpt-4-turbo"
