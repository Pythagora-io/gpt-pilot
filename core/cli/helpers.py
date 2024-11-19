import json
import os
import os.path
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from core.config import Config, LLMProvider, LocalIPCConfig, ProviderConfig, UIAdapter, get_config, loader
from core.config.env_importer import import_from_dotenv
from core.config.version import get_version
from core.db.session import SessionManager
from core.db.setup import run_migrations
from core.log import setup
from core.state.state_manager import StateManager
from core.ui.base import UIBase
from core.ui.console import PlainConsoleUI
from core.ui.ipc_client import IPCClientUI
from core.ui.virtual import VirtualUI


def parse_llm_endpoint(value: str) -> Optional[tuple[LLMProvider, str]]:
    """
    Parse --llm-endpoint command-line option.

    Option syntax is: --llm-endpoint <provider>:<url>

    :param value: Argument value.
    :return: Tuple with LLM provider and URL, or None if the option wasn't provided.
    """
    if not value:
        return None

    parts = value.split(":", 1)
    if len(parts) != 2:
        raise ArgumentTypeError("Invalid LLM endpoint format; expected 'provider:url'")

    try:
        provider = LLMProvider(parts[0])
    except ValueError as err:
        raise ArgumentTypeError(f"Unsupported LLM provider: {err}")
    url = urlparse(parts[1])
    if url.scheme not in ("http", "https"):
        raise ArgumentTypeError(f"Invalid LLM endpoint URL: {parts[1]}")

    return provider, url.geturl()


def parse_llm_key(value: str) -> Optional[tuple[LLMProvider, str]]:
    """
    Parse --llm-key command-line option.

    Option syntax is: --llm-key <provider>:<key>

    :param value: Argument value.
    :return: Tuple with LLM provider and key, or None if if the option wasn't provided.
    """
    if not value:
        return None

    parts = value.split(":", 1)
    if len(parts) != 2:
        raise ArgumentTypeError("Invalid LLM endpoint format; expected 'provider:key'")

    try:
        provider = LLMProvider(parts[0])
    except ValueError as err:
        raise ArgumentTypeError(f"Unsupported LLM provider: {err}")

    return provider, parts[1]


def parse_arguments() -> Namespace:
    """
    Parse command-line arguments.

    Available arguments:
        --help: Show the help message
        --config: Path to the configuration file
        --show-config: Output the default configuration to stdout
        --default-config: Output the configuration to stdout
        --level: Log level (debug,info,warning,error,critical)
        --database: Database URL
        --local-ipc-port: Local IPC port to connect to
        --local-ipc-host: Local IPC host to connect to
        --version: Show the version and exit
        --list: List all projects
        --list-json: List all projects in JSON format
        --project: Load a specific project
        --branch: Load a specific branch
        --step: Load a specific step in a project/branch
        --llm-endpoint: Use specific API endpoint for the given provider
        --llm-key: Use specific LLM key for the given provider
        --import-v0: Import data from a v0 (gpt-pilot) database with the given path
        --email: User's email address, if provided
        --extension-version: Version of the VSCode extension, if used
        --no-check: Disable initial LLM API check
        --use-git: Use Git for version control
    :return: Parsed arguments object.
    """
    version = get_version()

    parser = ArgumentParser()
    parser.add_argument("--config", help="Path to the configuration file", default="config.json")
    parser.add_argument("--show-config", help="Output the default configuration to stdout", action="store_true")
    parser.add_argument("--level", help="Log level (debug,info,warning,error,critical)", required=False)
    parser.add_argument("--database", help="Database URL", required=False)
    parser.add_argument("--local-ipc-port", help="Local IPC port to connect to", type=int, required=False)
    parser.add_argument("--local-ipc-host", help="Local IPC host to connect to", default="localhost", required=False)
    parser.add_argument("--version", action="version", version=version)
    parser.add_argument("--list", help="List all projects", action="store_true")
    parser.add_argument("--list-json", help="List all projects in JSON format", action="store_true")
    parser.add_argument("--project", help="Load a specific project", type=UUID, required=False)
    parser.add_argument("--branch", help="Load a specific branch", type=UUID, required=False)
    parser.add_argument("--step", help="Load a specific step in a project/branch", type=int, required=False)
    parser.add_argument("--delete", help="Delete a specific project", type=UUID, required=False)
    parser.add_argument(
        "--llm-endpoint",
        help="Use specific API endpoint for the given provider",
        type=parse_llm_endpoint,
        action="append",
        required=False,
    )
    parser.add_argument(
        "--llm-key",
        help="Use specific LLM key for the given provider",
        type=parse_llm_key,
        action="append",
        required=False,
    )
    parser.add_argument(
        "--import-v0",
        help="Import data from a v0 (gpt-pilot) database with the given path",
        required=False,
    )
    parser.add_argument("--email", help="User's email address", required=False)
    parser.add_argument("--extension-version", help="Version of the VSCode extension", required=False)
    parser.add_argument("--no-check", help="Disable initial LLM API check", action="store_true")
    parser.add_argument("--use-git", help="Use Git for version control", action="store_true", required=False)
    return parser.parse_args()


def load_config(args: Namespace) -> Optional[Config]:
    """
    Load Pythagora JSON configuration file and apply command-line arguments.

    :param args: Command-line arguments (at least `config` must be present).
    :return: Configuration object, or None if config couldn't be loaded.
    """
    if not os.path.isfile(args.config):
        imported = import_from_dotenv(args.config)
        if not imported:
            print(f"Configuration file not found: {args.config}; using default", file=sys.stderr)
            return get_config()

    try:
        config = loader.load(args.config)
    except ValueError as err:
        print(f"Error parsing config file {args.config}: {err}", file=sys.stderr)
        return None

    if args.level:
        config.log.level = args.level.upper()

    if args.database:
        config.db.url = args.database

    if args.local_ipc_port:
        config.ui = LocalIPCConfig(port=args.local_ipc_port, host=args.local_ipc_host)

    if args.llm_endpoint:
        for provider, endpoint in args.llm_endpoint:
            if provider not in config.llm:
                config.llm[provider] = ProviderConfig()
            config.llm[provider].base_url = endpoint

    if args.llm_key:
        for provider, key in args.llm_key:
            if provider not in config.llm:
                config.llm[provider] = ProviderConfig()
            config.llm[provider].api_key = key

    try:
        Config.model_validate(config)
    except ValueError as err:
        print(f"Configuration error: {err}", file=sys.stderr)
        return None

    return config


async def list_projects_json(db: SessionManager):
    """
    List all projects in the database in JSON format.
    """
    sm = StateManager(db)
    projects = await sm.list_projects()

    data = []
    for project in projects:
        last_updated = None
        p = {
            "name": project.name,
            "id": project.id.hex,
            "branches": [],
        }
        for branch in project.branches:
            b = {
                "name": branch.name,
                "id": branch.id.hex,
                "steps": [],
            }
            for state in branch.states:
                if not last_updated or state.created_at > last_updated:
                    last_updated = state.created_at
                s = {
                    "name": state.action or f"Step #{state.step_index}",
                    "step": state.step_index,
                }
                b["steps"].append(s)
            if b["steps"]:
                b["steps"][-1]["name"] = "Latest step"
            p["branches"].append(b)
        p["updated_at"] = last_updated.isoformat() if last_updated else None
        data.append(p)

    print(json.dumps(data, indent=2))


async def list_projects(db: SessionManager):
    """
    List all projects in the database.
    """
    sm = StateManager(db)
    projects = await sm.list_projects()

    print(f"Available projects ({len(projects)}):")
    for project in projects:
        print(f"* {project.name} ({project.id})")
        for branch in project.branches:
            last_step = max(state.step_index for state in branch.states)
            print(f"  - {branch.name} ({branch.id}) - last step: {last_step}")


async def load_project(
    sm: StateManager,
    project_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    step_index: Optional[int] = None,
) -> bool:
    """
    Load a project from the database.

    :param sm: State manager.
    :param project_id: Project ID (optional, loads the last step in the main branch).
    :param branch_id: Branch ID (optional, loads the last step in the branch).
    :param step_index: Step index (optional, loads the state at the given step).
    :return: True if the project was loaded successfully, False otherwise.
    """
    step_txt = f" step {step_index}" if step_index else ""

    if branch_id:
        project_state = await sm.load_project(branch_id=branch_id, step_index=step_index)
        if project_state:
            return True
        else:
            print(f"Branch {branch_id}{step_txt} not found; use --list to list all projects", file=sys.stderr)
            return False

    elif project_id:
        project_state = await sm.load_project(project_id=project_id, step_index=step_index)
        if project_state:
            return True
        else:
            print(f"Project {project_id}{step_txt} not found; use --list to list all projects", file=sys.stderr)
            return False

    return False


async def delete_project(db: SessionManager, project_id: UUID) -> bool:
    """
    Delete a project from a database.

    :param sm: State manager.
    :param project_id: Project ID.
    :return: True if project was deleted, False otherwise.
    """

    sm = StateManager(db)
    return await sm.delete_project(project_id)


def show_config():
    """
    Print the current configuration to stdout.
    """
    cfg = get_config()
    print(cfg.model_dump_json(indent=2))


def init() -> tuple[UIBase, SessionManager, Namespace]:
    """
    Initialize the application.

    Loads configuration, sets up logging and UI, initializes the database
    and runs database migrations.

    :return: Tuple with UI, db session manager, file manager, and command-line arguments.
    """
    args = parse_arguments()
    config = load_config(args)
    if not config:
        return (None, None, args)

    setup(config.log, force=True)

    if config.ui.type == UIAdapter.IPC_CLIENT:
        ui = IPCClientUI(config.ui)
    elif config.ui.type == UIAdapter.VIRTUAL:
        ui = VirtualUI(config.ui.inputs)
    else:
        ui = PlainConsoleUI()

    run_migrations(config.db)
    db = SessionManager(config.db)

    return (ui, db, args)


__all__ = ["parse_arguments", "load_config", "list_projects_json", "list_projects", "load_project", "init"]
