from io import StringIO
import json
from os.path import expanduser, expandvars, join
from os import getenv
from pathlib import Path
from subprocess import check_output
import sys
from unittest.mock import patch, MagicMock

import pytest

from utils.settings import (
    Loader,
    Settings,
    get_git_commit,
    get_package_version,
    get_version,
)


@pytest.fixture
def expected_config_location():
    xdg_config_home = getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return join(xdg_config_home, "gpt-pilot", "config.json")
    elif sys.platform in ["darwin", "linux"]:
        return expanduser("~/.gpt-pilot/config.json")
    elif sys.platform == "win32":
        return expandvars("%APPDATA%\\GPT Pilot\\config.json")
    else:
        raise RuntimeError(f"Unknown platform: {sys.platform}")


def test_settings_initializes_known_variables():
    settings = Settings()
    assert settings.openai_api_key is None
    assert settings.telemetry is None


def test_settings_init_ignores_unknown_variables():
    settings = Settings(unknown="value")
    assert not hasattr(settings, "unknown")


def test_settings_forbids_saving_unknown_variables():
    settings = Settings()

    with pytest.raises(AttributeError):
        settings.unknown = "value"


def test_settings_update():
    settings = Settings()
    settings.update(openai_api_key="test_key")
    assert settings.openai_api_key == "test_key"


def test_settings_to_dict():
    settings = Settings()
    settings.update(openai_api_key="test_key")
    assert dict(settings) == {
        "openai_api_key": "test_key",
        "telemetry": None,
    }


def test_loader_config_file_location(expected_config_location):
    settings = Settings()
    Loader(settings).config_path == expected_config_location


@patch("utils.settings.open")
@patch("utils.settings.Loader.update_settings_from_env")
def test_loader_load_config_file(_mock_from_env, mock_open, expected_config_location):
    settings = Settings()
    fake_config = json.dumps(
        {
            "openai_api_key": "test_key",
            "telemetry": {
                "id": "fake-id",
                "endpoint": "https://example.com",
            },
        }
    )
    mock_open.return_value.__enter__.return_value = StringIO(fake_config)

    loader = Loader(settings)
    assert loader.config_path == Path(expected_config_location)

    loader.config_path = MagicMock()
    loader.load()

    loader.config_path.exists.assert_called_once_with()
    mock_open.assert_called_once_with(loader.config_path, "r", encoding="utf-8")

    assert settings.openai_api_key == "test_key"
    assert settings.telemetry["id"] == "fake-id"
    assert settings.telemetry["endpoint"] == "https://example.com"


@patch("utils.settings.open")
@patch("utils.settings.Loader.update_settings_from_env")
def test_loader_load_no_config_file(_mock_from_env, mock_open, expected_config_location):
    settings = Settings()
    loader = Loader(settings)
    assert loader.config_path == Path(expected_config_location)

    loader.config_path = MagicMock()
    loader.config_path.exists.return_value = False
    loader.load()

    loader.config_path.exists.assert_called_once_with()
    mock_open.assert_not_called()

    assert settings.openai_api_key is None
    assert settings.telemetry is None


@patch("utils.settings.getenv")
def test_loader_load_from_env(mock_getenv):
    settings = Settings()
    mock_getenv.side_effect = lambda key: {
        "TELEMETRY_ID": "fake-id",
        "TELEMETRY_ENDPOINT": "https://example.com",
        "OPENAI_API_KEY": "test_key",
    }.get(key)

    Loader(settings).update_settings_from_env(settings)
    assert settings.openai_api_key == "test_key"
    assert settings.telemetry["id"] == "fake-id"
    assert settings.telemetry["endpoint"] == "https://example.com"


def test_get_git_commit():
    try:
        expected_commit_hash = check_output(
            ["git", "rev-parse", "HEAD"], encoding="ascii"
        ).strip()
    except Exception:
        expected_commit_hash = None

    assert get_git_commit() == expected_commit_hash


def test_get_package_version():
    assert get_package_version().startswith("0.0.")


def test_get_version():
    try:
        commit_suffix = (
            "-git"
            + check_output(["git", "rev-parse", "HEAD"], encoding="ascii").strip()[:7]
        )
    except Exception:
        commit_suffix = ""

    assert get_version().endswith(commit_suffix)
