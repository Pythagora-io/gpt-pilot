from core.config import LLMProvider
from core.config.env_importer import convert_config


def test_convert_config():
    values = {
        "ENDPOINT": "OPENAI",
        "OPENAI_ENDPOINT": "",
        "OPENAI_API_KEY": "",
        "AZURE_API_KEY": "",
        "AZURE_ENDPOINT": "",
        "OPENROUTER_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "MODEL_NAME": "gpt-4-0125-preview",
        "MAX_TOKENS": "8192",
        "DB_NAME": "gpt-pilot",
        "DB_HOST": "",
        "DB_PORT": "",
        "DB_USER": "",
        "DB_PASSWORD": "",
        "IGNORE_PATHS": "folder1,folder2",
    }
    config = convert_config(values)

    assert config.llm[LLMProvider.OPENAI].base_url is None
    assert config.llm[LLMProvider.OPENAI].api_key is None
    assert "folder1" in config.fs.ignore_paths
    assert "folder2" in config.fs.ignore_paths


def test_convert_openai_config():
    values = {
        "ENDPOINT": "OPENAI",
        "OPENAI_ENDPOINT": "http://example.openai.com/v1/chat/completions",
        "OPENAI_API_KEY": "sk-mykey",
        "MODEL_NAME": "gpt-4o",
    }
    config = convert_config(values)

    assert config.llm[LLMProvider.OPENAI].base_url == "http://example.openai.com/v1/"
    assert config.llm[LLMProvider.OPENAI].api_key == "sk-mykey"
    assert config.agent["default"].model == "gpt-4o"


def test_convert_azure_config():
    values = {
        "ENDPOINT": "AZURE",
        "AZURE_ENDPOINT": "http://openai.azure.com/v1/chat/completions",
        "AZURE_API_KEY": "sk-mykey",
    }
    config = convert_config(values)

    assert config.llm[LLMProvider.OPENAI].base_url == "http://openai.azure.com/v1/"
    assert config.llm[LLMProvider.OPENAI].api_key == "sk-mykey"


def test_convert_openrouter_config():
    values = {
        "ENDPOINT": "OPENROUTER",
        "OPENROUTER_ENDPOINT": "https://openrouter.ai/api/v1/chat/completions",
        "OPENROUTER_API_KEY": "sk-or-v1-mykey",
    }
    config = convert_config(values)

    assert config.llm[LLMProvider.OPENAI].base_url == "https://openrouter.ai/api/v1/"
    assert config.llm[LLMProvider.OPENAI].api_key == "sk-or-v1-mykey"


def test_convert_anthropic_config():
    values = {
        "ENDPOINT": "OPENAI",
        "ANTHROPIC_ENDPOINT": None,
        "ANTHROPIC_API_KEY": "sk-anthropic",
        "MODEL_NAME": "anthropic/claude",
    }
    config = convert_config(values)

    assert config.llm[LLMProvider.ANTHROPIC].base_url is None
    assert config.llm[LLMProvider.ANTHROPIC].api_key == "sk-anthropic"
    assert config.agent["default"].model == "claude"
