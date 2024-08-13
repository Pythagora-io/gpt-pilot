from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ProjectStage(str, Enum):
    DESCRIPTION = "project_description"
    ARCHITECTURE = "architecture"
    CODING = "coding"


class UIClosedError(Exception):
    """The user interface has been closed (user stoped Pythagora)."""


class UISource:
    """
    Source for UI messages.

    See also: `AgentSource`

    Attributes:
    * `display_name`: Human-readable name of the source.
    * `type_name`: Type name of the source (used in IPC)
    """

    display_name: str
    type_name: str

    def __init__(self, display_name: str, type_name: str):
        """
        Create a new UI source.

        :param display_name: Human-readable name of the source.
        :param type_name: Type name of the source (used in IPC)
        """
        self.display_name = display_name
        self.type_name = type_name

    def __str__(self) -> str:
        return self.display_name


class AgentSource(UISource):
    """
    Agent UI source.

    Attributes:
    * `display_name`: Human-readable name of the agent (eg. "Product Owner").
    * `type_name`: Type of the agent (eg. "agent:product-owner").
    """

    def __init__(self, display_name: str, agent_type: str):
        """
        Create a new agent source.

        :param display_name: Human-readable name of the agent.
        :param agent_type: Type of the agent.
        """
        super().__init__(display_name, f"agent:{agent_type}")


class UserInput(BaseModel):
    """
    Represents user input.

    See also: `UIBase.ask_question()`

    Attributes:
    * `text`: User-provided text (if any).
    * `button`: Name (key) of the button the user selected (if any).
    * `cancelled`: Whether the user cancelled the input.
    """

    text: Optional[str] = None
    button: Optional[str] = None
    cancelled: bool = False


class UIBase:
    """
    Base class for UI adapters.
    """

    async def start(self) -> bool:
        """
        Start the UI adapter.

        :return: Whether the UI was started successfully.
        """
        raise NotImplementedError()

    async def stop(self):
        """
        Stop the UI adapter.
        """
        raise NotImplementedError()

    async def send_stream_chunk(self, chunk: str, *, source: Optional[UISource] = None):
        """
        Send a chunk of the stream to the UI.

        :param chunk: Chunk of the stream.
        :param source: Source of the stream (if any).
        """
        raise NotImplementedError()

    async def send_message(self, message: str, *, source: Optional[UISource] = None):
        """
        Send a complete message to the UI.

        :param message: Message content.
        :param source: Source of the message (if any).
        """
        raise NotImplementedError()

    async def send_key_expired(self, message: Optional[str] = None):
        """
        Send the key expired message.
        """
        raise NotImplementedError()

    async def send_app_finished(
        self,
        app_id: Optional[str] = None,
        app_name: Optional[str] = None,
        folder_name: Optional[str] = None,
    ):
        """
        Send the app finished message.

        :param app_id: App ID.
        :param app_name: App name.
        :param folder_name: Folder name.
        """
        raise NotImplementedError()

    async def send_feature_finished(
        self,
        app_id: Optional[str] = None,
        app_name: Optional[str] = None,
        folder_name: Optional[str] = None,
    ):
        """
        Send the feature finished message.

        :param app_id: App ID.
        :param app_name: App name.
        :param folder_name: Folder name.
        """
        raise NotImplementedError()

    async def ask_question(
        self,
        question: str,
        *,
        buttons: Optional[dict[str, str]] = None,
        default: Optional[str] = None,
        buttons_only: bool = False,
        allow_empty: bool = False,
        hint: Optional[str] = None,
        initial_text: Optional[str] = None,
        source: Optional[UISource] = None,
    ) -> UserInput:
        """
        Ask the user a question.

        If buttons are provided, the UI should use the item values
        as button labels, and item keys as the values to return.

        After the user answers, constructs a `UserInput` object
        with the selected button or text. If the user cancels
        the input, the `cancelled` attribute should be set to True.

        :param question: Question to ask.
        :param buttons: Buttons to display (if any).
        :param default: Default value (if user provides no input).
        :param buttons_only: Whether to only show buttons (disallow custom text).
        :param allow_empty: Whether to allow empty input.
        :param source: Source of the question (if any).
        :return: User input.
        """
        raise NotImplementedError()

    async def send_project_stage(self, stage: ProjectStage):
        """
        Send a project stage to the UI.

        :param stage: Project stage.
        """
        raise NotImplementedError()

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
        """
        Send a task progress update to the UI.

        :param index: Index of the current task, starting from 1.
        :param n_tasks: Total number of tasks.
        :param description: Description of the task.
        :param source: Source of the task, one of: 'app', 'feature', 'debugger', 'troubleshooting', 'review'.
        :param status: Status of the task, can be 'in_progress' or 'done'.
        :param source_index: Index of the source.
        :param tasks: List of all tasks.
        """
        raise NotImplementedError()

    async def send_step_progress(
        self,
        index: int,
        n_steps: int,
        step: dict,
        task_source: str,
    ):
        """
        Send a step progress update to the UI.

        :param index: Index of the step within the current task, starting from 1.
        :param n_steps: Number of steps in the current task.
        :param step: Step data.
        :param task_source: Source of the task, one of: 'app', 'feature', 'debugger', 'troubleshooting', 'review'.
        """
        raise NotImplementedError()

    async def send_modified_files(
        self,
        modified_files: dict[str, str, str],
    ):
        """
        Send a list of modified files to the UI.

        :param modified_files: List of modified files.
        """
        raise NotImplementedError()

    async def send_data_about_logs(
        self,
        data_about_logs: dict,
    ):
        """
        Send the data about debugging logs.

        :param data_about_logs: Data about logs.
        """
        raise NotImplementedError()

    async def send_run_command(self, run_command: str):
        """
        Send a run command to the UI.

        :param run_command: Run command.
        """
        raise NotImplementedError()

    async def open_editor(self, file: str, line: Optional[int] = None):
        """
        Open an editor at the specified file and line.

        :param file: File to open.
        :param line: Line to highlight.
        """
        raise NotImplementedError()

    async def send_project_root(self, path: str):
        """
        Tell UI component about the project root path.

        :param path: Project root path.
        """
        raise NotImplementedError()

    async def start_important_stream(self, path: str):
        """
        Tell the extension that next stream should be visible and rendered as markdown

        """
        raise NotImplementedError()

    async def send_project_stats(self, stats: dict):
        """
        Send project statistics to the UI.

        The stats object should have the following keys:
        * `num_lines` - Total number of lines in the project
        * `num_files` - Number of files in the project
        * `num_tokens` - Number of tokens used for LLM requests in this session

        :param stats: Project statistics.
        """
        raise NotImplementedError()

    async def generate_diff(self, file_old: str, file_new: str):
        """
        Generate a diff between two files.

        :param file_old: Old file content.
        :param file_new: New file content.
        """
        raise NotImplementedError()

    async def close_diff(self):
        """
        Close all diff views.
        """
        raise NotImplementedError()

    async def loading_finished(self):
        """
        Notify the UI that loading has finished.
        """
        raise NotImplementedError()

    async def send_project_description(self, description: str):
        """
        Send the project description to the UI.

        :param description: Project description.
        """
        raise NotImplementedError()

    async def send_features_list(self, features: list[str]):
        """
        Send the summaries of implemented features to the UI.

        Features are epics after the initial one (initial project).

        :param features: List of feature summaries.
        """
        raise NotImplementedError()

    async def import_project(self, project_dir: str):
        """
        Ask the UI to import files from the project directory.

        The UI should provide a way for the user to select the directory with
        existing project, and recursively copy the files over.

        :param project_dir: Project directory.
        """
        raise NotImplementedError()


pythagora_source = UISource("Pythagora", "pythagora")
success_source = UISource("Congratulations", "success")


__all__ = [
    "UISource",
    "AgentSource",
    "UserInput",
    "UIBase",
    "pythagora_source",
    "success_source",
]
