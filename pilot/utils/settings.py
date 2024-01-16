import ast
import json
from logging import getLogger
from os import getenv, makedirs
from pathlib import Path
import sys
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

log = getLogger(__name__)

AVAILABLE_SETTINGS = [
    "telemetry",
    "openai_api_key",
]


class Settings:
    """
    Application settings

    This object holds all the settings for the application, whether they are
    loaded from the config file, set via environment variables or the command
    line arguments.

    Available settings are listed in the `AVAILABLE_SETTINGS` list.

    This is a singleton object, use it by importing the instance
    directly from the module:

    >>> from utils.settings import settings

    To get a setting:

    >>> settings.openai_api_key

    To get all settings as a dictionary:

    >>> dict(settings)

    To set (update) one setting:

    >>> settings.openai_api_key = "test_key"

    To update multiple settings at once:

    >>> settings.update(openai_api_key="test_key", telemetry=None)

    Note: updating settings will not save them to the config file.
    To do that, use the `loader.save()` method:

    >>> from utils.settings import loader
    >>> loader.save("openai_api_key", "telemetry")

    To see all available settings:

    >>> from utils.settings import AVAILABLE_SETTINGS
    >>> print(AVAILABLE_SETTINGS)
    """

    # Available settings.
    __slots__ = AVAILABLE_SETTINGS

    def __init__(self, **kwargs):
        for key in self.__slots__:
            setattr(self, key, None)

        self.update(**kwargs)

    def __iter__(self):
        for key in self.__slots__:
            yield key, getattr(self, key)

    def update(self, **kwargs):
        """
        Update settings.

        :param kwargs: settings to update (name=value)
        """
        for key, value in kwargs.items():
            try:
                setattr(self, key, value)
            except AttributeError:
                log.warning(f"Ignoring unknown setting: {key}")


class Loader:
    """
    Loader for application settings.

    The app settings are stored in a JSON file in the config directory.

    The config directory is determined by the following rules:
    * If the XDG_CONFIG_HOME environment variable is set (desktop Linux), use that.
    * If the APPDATA environment variable is set (Windows), use that.
    * Otherwise, use the POSIX default ~/.<app-name> (MacOS, server Linux).

    Settings from the config file can be overridden by environment variables
    (all caps) or command line arguments.

    This is a singleton object, use it by importing the instance directly
    from the module:

    >>> from utils.settings import loader

    This will load the settings automatically.

    To get the config file location:

    >>> from utils.settings import config_path
    >>> print(config_path)

    To get the current version of GPT Pilot:

    >>> from utils.settings import version
    >>> print(version)
    """

    APP_NAME = "GPT Pilot"

    def __init__(self, settings: Settings):
        self.config_dir = self.resolve_config_dir()
        self.config_path = self.config_dir / "config.json"
        self.settings = settings

    def load(self):
        """
        Load settings from the config file, environment
        variables and the command-line arguments.
        """
        self.settings.update(**self._load_config())
        self.update_settings_from_env(self.settings)
        self.update_settings_from_args(self.settings)

    @classmethod
    def resolve_config_dir(cls) -> Path:
        """
        Figure out where to store the config file(s).

        :return: path to the desired location config directory

        See the clas docstring for details on how the config directory is
        determined.
        """
        posix_app_name = cls.APP_NAME.replace(" ", "-").lower()

        xdg_config_home = getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home) / Path(posix_app_name)

        if sys.platform == "win32" and getenv("APPDATA"):
            return Path(getenv("APPDATA")) / Path(cls.APP_NAME)

        return Path("~").expanduser() / Path(f".{posix_app_name}")

    def _load_config(self) -> dict[str, Any]:
        """
        Load settings from the config file.

        :returns: dict of settings loaded from the config file

        If the file doesn't exist or there is an error loading the
        config file, an empty settings dict will be returned.

        This is a low-level method used automatically by `Loader.load()`.
        """

        if not self.config_path.exists():
            log.debug(f"Config file not found: {self.config_path}")
            return {}

        log.debug(f"Loading settings from config file: {self.config_path}")
        try:
            with open(self.config_path, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as e:
            log.error(
                f"Error loading config file {self.config_path}: {e}", exc_info=True
            )
            return {}

    def _save_config(self, config: dict[str, Any]):
        """
        Save provided settings to the config file.

        :param config: dict of settings to save

        This is a low-level method that will overwrite the entire
        config with what's passed in. You should probably use
        `update()` instead.
        """

        if not self.config_dir.exists():
            log.debug(f"Creating config directory: {self.config_dir}")
            makedirs(self.config_dir, exist_ok=True)

        log.debug(f"Saving settings to config file: {self.config_path}")
        with open(self.config_path, "w", encoding="utf-8") as fp:
            json.dump(config, fp, indent=2, sort_keys=True)

    def save(self, *args: list[str]):
        """
        Save one or more settings to the config file, creating it
        if neccessary.

        :param args: list of setting names to set

        This method will update the current config file with
        *ONLY* the settings listed here.

        The reason we don't want to store all settings is that some
        might have been overridden from environment variables or
        command line arguments, that might be temporary.

        We don't want to overwrite the config file with those
        (potentially temporary) values.
        """

        settings_from_config = self._load_config()
        for key in args:
            try:
                value = getattr(self.settings, key)
                settings_from_config[key] = value
            except AttributeError:
                pass

        self._save_config(settings_from_config)

    def update_settings_from_env(self, settings: Settings):
        """
        Update settings from environment variables.

        :param settings: Settings object to update in-place

        Note that environment variable names are hardcoded here,
        because they're not always the same as the setting names.
        """
        # Telemetry (see utils.telemetry)
        telemetry_id = getenv("TELEMETRY_ID")
        telemetry_endpoint = getenv("TELEMETRY_ENDPOINT")

        if settings.telemetry is None and (telemetry_id or telemetry_endpoint):
            settings.telemetry = {}

        if telemetry_id:
            settings.telemetry["id"] = telemetry_id
        if telemetry_endpoint:
            settings.telemetry["endpoint"] = telemetry_endpoint

        # OpenAI API key
        openai_api_key = getenv("OPENAI_API_KEY")
        settings.openai_api_key = openai_api_key

    def update_settings_from_args(self, _settings: Settings):
        """
        Update settings from command line arguments.

        :param settings: Settings object to update in-place

        Note: this is not implemented yet, and currently does nothing.
        """
        # TODO: implement this
        pass


def get_git_commit() -> Optional[str]:
    """
    Return the current git commit (if running from a repo).

    :return: commit hash or None if not running from a git repo
    """
    git_dir = Path(__file__).parent.parent.parent / ".git"
    if not git_dir.is_dir():
        return None

    git_head = git_dir / "HEAD"
    if not git_head.is_file():
        return None

    with open(git_head, "r", encoding="utf-8") as fp:
        ref = fp.read().strip()
        if ref.startswith("ref: "):
            ref = ref[5:]
            with open(git_dir / ref, "r", encoding="utf-8") as fp:
                return fp.read().strip()
        else:
            return ref


def get_package_version() -> str:
    """
    Get package version.

    Note: until we have the packaging set up, this always returns "0.0.0".

    :return: package version as defined in setup.py
    """
    UNKNOWN = "0.0.0"

    setup_file = Path(__file__).parent.parent.parent / "setup.py"
    if not setup_file.is_file():
        return UNKNOWN

    try:
        with open(setup_file, "r", encoding="utf-8") as fp:
            code = ast.parse(fp.read(), filename="setup.py")
            for node in code.body:
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "VERSION"
                    and isinstance(node.value, ast.Constant)
                ):
                    return str(node.value.value)
    except:  # noqa
        return UNKNOWN



def get_version() -> str:
    """
    Find and return the current version of GPT Pilot.

    The version string is built from the package version and the current
    git commit hash (if running from a git repo).

    Example: 0.0.0-gitbf01c19

    :return: version string
    """

    version = get_package_version()
    commit = get_git_commit()
    if commit:
        version = version + "-git" + commit[:7]

    return version


version = get_version()
settings = Settings()
loader = Loader(settings)
loader.load()
config_path = loader.config_path


__all__ = ["version", "settings", "loader", "config_path"]
