import asyncio
import atexit
import signal
import sys
from argparse import Namespace
from asyncio import run

from core.agents.orchestrator import Orchestrator
from core.cli.helpers import delete_project, init, list_projects, list_projects_json, load_project, show_config
from core.config import LLMProvider, get_config
from core.db.session import SessionManager
from core.db.v0importer import LegacyDatabaseImporter
from core.llm.anthropic_client import CustomAssertionError
from core.llm.base import APIError, BaseLLMClient
from core.log import get_logger
from core.state.state_manager import StateManager
from core.telemetry import telemetry
from core.ui.base import ProjectStage, UIBase, UIClosedError, UserInput, pythagora_source

log = get_logger(__name__)


telemetry_sent = False


async def cleanup(ui: UIBase):
    global telemetry_sent
    if not telemetry_sent:
        await telemetry.send()
        telemetry_sent = True
    await ui.stop()


def sync_cleanup(ui: UIBase):
    asyncio.run(cleanup(ui))


async def run_project(sm: StateManager, ui: UIBase, args) -> bool:
    """
    Work on the project.

    Starts the orchestrator agent with the newly loaded/created project
    and runs it until the orchestrator decides to exit.

    :param sm: State manager.
    :param ui: User interface.
    :param args: Command-line arguments.
    :return: True if the orchestrator exited successfully, False otherwise.
    """

    telemetry.set("app_id", str(sm.project.id))
    telemetry.set("initial_prompt", sm.current_state.specification.description)

    orca = Orchestrator(sm, ui, args=args)
    success = False
    try:
        success = await orca.run()
        telemetry.set("end_result", "success:exit" if success else "failure:api-error")
    except (KeyboardInterrupt, UIClosedError):
        log.info("Interrupted by user")
        telemetry.set("end_result", "interrupt")
        await sm.rollback()
    except APIError as err:
        log.warning(f"LLM API error occurred: {err.message}")
        await ui.send_message(
            f"Stopping Pythagora due to an error while calling the LLM API: {err.message}",
            source=pythagora_source,
        )
        telemetry.set("end_result", "failure:api-error")
        await sm.rollback()
    except CustomAssertionError as err:
        log.warning(f"Anthropic assertion error occurred: {str(err)}")
        await ui.send_message(
            f"Stopping Pythagora due to an error inside Anthropic SDK. {str(err)}",
            source=pythagora_source,
        )
        telemetry.set("end_result", "failure:assertion-error")
        await sm.rollback()
    except Exception as err:
        log.error(f"Uncaught exception: {err}", exc_info=True)
        stack_trace = telemetry.record_crash(err)
        await sm.rollback()
        await ui.send_message(
            f"Stopping Pythagora due to error:\n\n{stack_trace}",
            source=pythagora_source,
        )

    return success


async def llm_api_check(ui: UIBase) -> bool:
    """
    Check whether the configured LLMs are reachable in parallel.

    :param ui: UI we'll use to report any issues
    :return: True if all the LLMs are reachable.
    """

    config = get_config()

    async def handler(*args, **kwargs):
        pass

    checked_llms: set[LLMProvider] = set()
    tasks = []

    async def check_llm(llm_config):
        if llm_config.provider + llm_config.model in checked_llms:
            return True

        checked_llms.add(llm_config.provider + llm_config.model)
        client_class = BaseLLMClient.for_provider(llm_config.provider)
        llm_client = client_class(llm_config, stream_handler=handler, error_handler=handler)
        try:
            resp = await llm_client.api_check()
            if not resp:
                await ui.send_message(
                    f"API check for {llm_config.provider.value} {llm_config.model} failed.",
                    source=pythagora_source,
                )
                log.warning(f"API check for {llm_config.provider.value} {llm_config.model} failed.")
                return False
            else:
                log.info(f"API check for {llm_config.provider.value} {llm_config.model} succeeded.")
                return True
        except APIError as err:
            await ui.send_message(
                f"API check for {llm_config.provider.value} {llm_config.model} failed with: {err}",
                source=pythagora_source,
            )
            log.warning(f"API check for {llm_config.provider.value} failed with: {err}")
            return False

    for llm_config in config.all_llms():
        tasks.append(check_llm(llm_config))

    results = await asyncio.gather(*tasks)

    success = all(results)

    if not success:
        telemetry.set("end_result", "failure:api-error")

    return success


async def start_new_project(sm: StateManager, ui: UIBase) -> bool:
    """
    Start a new project.

    :param sm: State manager.
    :param ui: User interface.
    :return: True if the project was created successfully, False otherwise.
    """

    stack = await ui.ask_question(
        "What do you want to use to build your app?",
        allow_empty=False,
        buttons={"node": "Node.js", "other": "Other (coming soon)"},
        buttons_only=True,
        source=pythagora_source,
        full_screen=True,
    )

    if stack.button == "other":
        language = await ui.ask_question(
            "What language you want to use?",
            allow_empty=False,
            source=pythagora_source,
            full_screen=True,
        )
        await telemetry.trace_code_event(
            "stack-choice-other",
            {"language": language.text},
        )
        await ui.send_message("Thank you for submitting your request to support other languages.")
        return False
    elif stack.button == "node":
        await telemetry.trace_code_event(
            "stack-choice",
            {"language": "node"},
        )
    elif stack.button == "python":
        await telemetry.trace_code_event(
            "stack-choice",
            {"language": "python"},
        )

    while True:
        try:
            await ui.send_project_stage({"stage": ProjectStage.PROJECT_NAME})
            user_input = await ui.ask_question(
                "What is the project name?",
                allow_empty=False,
                source=pythagora_source,
                full_screen=True,
            )
        except (KeyboardInterrupt, UIClosedError):
            user_input = UserInput(cancelled=True)

        if user_input.cancelled:
            return False

        project_name = user_input.text.strip()
        if not project_name:
            await ui.send_message("Please choose a project name", source=pythagora_source)
        elif len(project_name) > 100:
            await ui.send_message("Please choose a shorter project name", source=pythagora_source)
        else:
            break

    project_state = await sm.create_project(project_name)
    return project_state is not None


async def run_pythagora_session(sm: StateManager, ui: UIBase, args: Namespace):
    """
    Run a Pythagora session.

    :param sm: State manager.
    :param ui: User interface.
    :param args: Command-line arguments.
    :return: True if the application ran successfully, False otherwise.
    """

    if not args.no_check:
        if not await llm_api_check(ui):
            await ui.send_message(
                "Pythagora cannot start because the LLM API is not reachable.",
                source=pythagora_source,
            )
            return False

    if args.project or args.branch or args.step:
        telemetry.set("is_continuation", True)
        success = await load_project(sm, args.project, args.branch, args.step)
        if not success:
            return False
    else:
        success = await start_new_project(sm, ui)
        if not success:
            return False

    return await run_project(sm, ui, args)


async def async_main(
    ui: UIBase,
    db: SessionManager,
    args: Namespace,
) -> bool:
    """
    Main application coroutine.

    :param ui: User interface.
    :param db: Database session manager.
    :param args: Command-line arguments.
    :return: True if the application ran successfully, False otherwise.
    """
    global telemetry_sent

    if args.list:
        await list_projects(db)
        return True
    elif args.list_json:
        await list_projects_json(db)
        return True
    if args.show_config:
        show_config()
        return True
    elif args.import_v0:
        importer = LegacyDatabaseImporter(db, args.import_v0)
        await importer.import_database()
        return True
    elif args.delete:
        success = await delete_project(db, args.delete)
        return success

    telemetry.set("user_contact", args.email)
    if args.extension_version:
        telemetry.set("is_extension", True)
        telemetry.set("extension_version", args.extension_version)

    sm = StateManager(db, ui)
    ui_started = await ui.start()
    if not ui_started:
        return False

    telemetry.start()

    # Set up signal handlers
    def signal_handler(sig, frame):
        if not telemetry_sent:
            sync_cleanup(ui)
        sys.exit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    # Register the cleanup function
    atexit.register(sync_cleanup, ui)

    try:
        success = await run_pythagora_session(sm, ui, args)
    finally:
        await cleanup(ui)

    return success


def run_pythagora():
    ui, db, args = init()
    if not ui or not db:
        return -1
    success = run(async_main(ui, db, args))
    return 0 if success else -1


if __name__ == "__main__":
    sys.exit(run_pythagora())
