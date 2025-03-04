from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
import numpy as np
from sklearn.ensemble import IsolationForest

class ProjectStage(str, Enum):
    DESCRIPTION = "project_description"
    ARCHITECTURE = "architecture"
    CODING = "coding"

class UIClosedError(Exception):
    """The user interface has been closed (user stopped Pythagora)."""

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

class AIModel:
    """
    AI Model for predicting user interactions and detecting anomalies.

    Attributes:
    * `model`: The IsolationForest model instance.
    * `data`: Historical interaction data.
    """

    def __init__(self):
        self.model = IsolationForest(random_state=42)
        self.data = []

    def update_data(self, new_data: np.ndarray):
        """Update historical interaction data and retrain the model."""
        self.data.extend(new_data)
        if len(self.data) > 1:
            self.model.fit(np.array(self.data))

    def predict(self, data_point: np.ndarray) -> int:
        """Predict if the data point is an anomaly."""
        return self.model.predict([data_point])[0]

ai_model = AIModel()

class UIBase:
    """
    Base class for UI adapters with AI integration for enhanced interaction predictions.
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
        buttons: Optional[Dict[str, str]] = None,
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
        tasks: Optional[list[Dict[str, Any]]] = None,
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
        step: Dict[str, Any],
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

    async def send_project_stats(self, stats: Dict[str, Any]):
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

    async def predict_user_interaction(self, user_input: UserInput) -> str:
        """
        Predict user behavior based on historical interaction data.

        :param user_input: The user input data to predict behavior.
        :return: Predicted behavior or interaction.
        """
        input_data = np.array([user_input.text or '', user_input.button or '']).reshape(1, -1)
        ai_model.update_data(input_data)
        prediction = ai_model.predict(input_data[0])
        return "Anomaly detected" if prediction == -1 else "Normal behavior"

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
