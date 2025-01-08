from typing import Optional

from prompt_toolkit.shortcuts import PromptSession

from core.log import get_logger
from core.ui.base import UIBase, UIClosedError, UISource, UserInput

log = get_logger(__name__)


class PlainConsoleUI(UIBase):
    """
    UI adapter for plain (no color) console output.
    """

    async def start(self) -> bool:
        log.debug("Starting console UI")
        return True

    async def stop(self):
        log.debug("Stopping console UI")

    async def send_stream_chunk(
        self, chunk: Optional[str], *, source: Optional[UISource] = None, project_state_id: Optional[str] = None
    ):
        if chunk is None:
            # end of stream
            print("", flush=True)
        else:
            print(chunk, end="", flush=True)

    async def send_message(
        self,
        message: str,
        *,
        source: Optional[UISource] = None,
        project_state_id: Optional[str] = None,
        extra_info: Optional[str] = None,
    ):
        if source:
            print(f"[{source}] {message}")
        else:
            print(message)

    async def send_key_expired(self, message: Optional[str] = None):
        if message:
            await self.send_message(message)

    async def send_app_finished(
        self,
        app_id: Optional[str] = None,
        app_name: Optional[str] = None,
        folder_name: Optional[str] = None,
    ):
        pass

    async def send_feature_finished(
        self,
        app_id: Optional[str] = None,
        app_name: Optional[str] = None,
        folder_name: Optional[str] = None,
    ):
        pass

    async def ask_question(
        self,
        question: str,
        *,
        buttons: Optional[dict[str, str]] = None,
        default: Optional[str] = None,
        buttons_only: bool = False,
        allow_empty: bool = False,
        full_screen: Optional[bool] = False,
        hint: Optional[str] = None,
        verbose: bool = True,
        initial_text: Optional[str] = None,
        source: Optional[UISource] = None,
        project_state_id: Optional[str] = None,
        extra_info: Optional[str] = None,
        placeholder: Optional[str] = None,
    ) -> UserInput:
        if source:
            print(f"[{source}] {question}")
        else:
            print(f"{question}")

        if buttons:
            for k, v in buttons.items():
                default_str = " (default)" if k == default else ""
                print(f"  [{k}]: {v}{default_str}")

        session = PromptSession("> ")

        while True:
            try:
                choice = await session.prompt_async(default=initial_text or "")
                choice = choice.strip()
            except KeyboardInterrupt:
                raise UIClosedError()
            if not choice and default:
                choice = default
            if buttons and choice in buttons:
                return UserInput(button=choice, text=None)
            if buttons_only:
                print("Please choose one of available options")
                continue
            if choice or allow_empty:
                return UserInput(button=None, text=choice)
            print("Please provide a valid input")

    async def send_project_stage(self, data: dict):
        pass

    async def send_epics_and_tasks(
        self,
        epics: list[dict],
        tasks: list[dict],
    ):
        pass

    async def send_task_progress(
        self,
        index: int,
        n_tasks: int,
        description: str,
        source: str,
        status: str,
        source_index: int = 1,
        tasks: list[dict] = None,
    ):
        pass

    async def send_step_progress(
        self,
        index: int,
        n_steps: int,
        step: dict,
        task_source: str,
    ):
        pass

    async def send_modified_files(
        self,
        modified_files: dict[str, str, str],
    ):
        pass

    async def send_data_about_logs(
        self,
        data_about_logs: dict,
    ):
        pass

    async def send_run_command(self, run_command: str):
        pass

    async def send_app_link(self, app_link: str):
        pass

    async def open_editor(self, file: str, line: Optional[int] = None):
        pass

    async def send_project_root(self, path: str):
        pass

    async def send_project_stats(self, stats: dict):
        pass

    async def send_test_instructions(self, test_instructions: str, project_state_id: Optional[str] = None):
        pass

    async def knowledge_base_update(self, knowledge_base: dict):
        pass

    async def send_file_status(self, file_path: str, file_status: str, source: Optional[UISource] = None):
        pass

    async def send_bug_hunter_status(self, status: str, num_cycles: int):
        pass

    async def generate_diff(
        self,
        file_path: str,
        file_old: str,
        file_new: str,
        n_new_lines: int = 0,
        n_del_lines: int = 0,
        source: Optional[UISource] = None,
    ):
        pass

    async def stop_app(self):
        pass

    async def close_diff(self):
        pass

    async def loading_finished(self):
        pass

    async def send_project_description(self, description: str):
        pass

    async def send_features_list(self, features: list[str]):
        pass

    async def import_project(self, project_dir: str):
        pass

    async def start_important_stream(self):
        pass

    async def start_breakdown_stream(self):
        pass


__all__ = ["PlainConsoleUI"]
