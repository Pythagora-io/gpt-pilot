import sys
from os import getenv, makedirs
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr

from core.log import get_logger

log = get_logger(__name__)


SETTINGS_APP_NAME = "GPT Pilot"
DEFAULT_TELEMETRY_ENDPOINT = "https://api.pythagora.io/telemetry"


class TelemetrySettings(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex, description="Unique telemetry ID")
    enabled: bool = Field(True, description="Whether telemetry should send stats to the server")
    endpoint: str = Field(DEFAULT_TELEMETRY_ENDPOINT, description="Telemetry server endpoint")


def resolve_config_dir() -> Path:
    """
    Figure out where to store the global config file(s).

    :return: path to the desired location config directory

    See the UserSettings docstring for details on how the config directory is
    determined.
    """
    posix_app_name = SETTINGS_APP_NAME.replace(" ", "-").lower()

    xdg_config_home = getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / Path(posix_app_name)

    if sys.platform == "win32" and getenv("APPDATA"):
        return Path(getenv("APPDATA")) / Path(SETTINGS_APP_NAME)

    return Path("~").expanduser() / Path(f".{posix_app_name}")


class UserSettings(BaseModel):
    """
    This object holds all the global user settings, that are applicable for
    all Pythagora/GPT-Pilot installations.

    The use settings are stored in a JSON file in the config directory.

    The config directory is determined by the following rules:
    * If the XDG_CONFIG_HOME environment variable is set (desktop Linux), use that.
    * If the APPDATA environment variable is set (Windows), use that.
    * Otherwise, use the POSIX default ~/.<app-name> (MacOS, server Linux).

    This is a singleton object, use it by importing the instance directly
    from the module:

    >>> from config.user_settings import settings
    >>> print(settings.telemetry.id)
    >>> print(settings.config_path)
    """

    telemetry: TelemetrySettings = TelemetrySettings()
    _config_path: str = PrivateAttr("")

    @staticmethod
    def load():
        config_path = resolve_config_dir() / "config.json"

        if not config_path.exists():
            default = UserSettings()
            default._config_path = config_path
            default.save()

        with open(config_path, "r", encoding="utf-8") as fp:
            settings = UserSettings.model_validate_json(fp.read())
        settings._config_path = str(config_path)
        return settings

    def save(self):
        makedirs(Path(self._config_path).parent, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as fp:
            fp.write(self.model_dump_json(indent=2))

    @property
    def config_path(self):
        return self._config_path


settings = UserSettings.load()


__all__ = ["settings"]
