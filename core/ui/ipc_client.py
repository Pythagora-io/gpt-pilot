import asyncio
import json
from enum import Enum
from os.path import basename
from typing import Optional, Union

from pydantic import BaseModel, ValidationError

from core.config import LocalIPCConfig
from core.log import get_logger
from core.ui.base import ProjectStage, UIBase, UIClosedError, UISource, UserInput

VSCODE_EXTENSION_HOST = "localhost"
VSCODE_EXTENSION_PORT = 8125
MESSAGE_SIZE_LIMIT = 512 * 1024

log = get_logger(__name__)


# TODO: unify these (and corresponding changes in the extension) before release
# Also clean up (remove) double JSON encoding in some of the messages
class MessageType(str, Enum):
    EXIT = "exit"
    STREAM = "stream"
    VERBOSE = "verbose"
    BUTTONS = "button"
    BUTTONS_ONLY = "buttons-only"
    RESPONSE = "response"
    USER_INPUT_REQUEST = "user_input_request"
    INFO = "info"
    PROGRESS = "progress"
    DEBUGGING_LOGS = "debugging_logs"
    RUN_COMMAND = "run_command"
    OPEN_FILE = "openFile"
    PROJECT_FOLDER_NAME = "project_folder_name"
    PROJECT_STATS = "projectStats"
    HINT = "hint"
    KEY_EXPIRED = "keyExpired"
    INPUT_PREFILL = "inputPrefill"
    LOADING_FINISHED = "loadingFinished"
    PROJECT_DESCRIPTION = "projectDescription"
    FEATURES_LIST = "featuresList"
    IMPORT_PROJECT = "importProject"
    APP_FINISHED = "appFinished"
    FEATURE_FINISHED = "featureFinished"
    GENERATE_DIFF = "generateDiff"
    CLOSE_DIFF = "closeDiff"
    MODIFIED_FILES = "modifiedFiles"
    IMPORTANT_STREAM = "importantStream"


class Message(BaseModel):
    """
    Message structure for IPC communication with the VSCode extension.

    Attributes:
    * `type`: Message type (always "response" for VSC server responses)
    * `category`: Message category (eg. "agent:product-owner"), optional
    * `content`: Message content (eg. "Hello, how are you?"), optional
    """

    type: MessageType
    category: Optional[str] = None
    content: Union[str, dict, None] = None

    def to_bytes(self) -> bytes:
        """
        Convert Message instance to wire format.
        """
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(self, data: bytes) -> "Message":
        """
        Parses raw byte payload into a message.

        This is done in two phases. First, the bytes are UTF-8
        decoded and converted to a dict. Then, the dictionary
        structure is parsed into a Message object.

        This lets us raise different errors based on whether the
        data is not valid JSON or the JSON structure is not valid
        for a Message object.

        :param data: Raw byte payload.
        :return: Message object.
        """
        try:
            json_data = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            raise ValueError(f"Error decoding JSON: {err}") from err
        return Message.model_validate_json(json.dumps(json_data))


class IPCClientUI(UIBase):
    """
    UI adapter for Pythagora VSCode extension IPC.
    """

    def __init__(self, config: LocalIPCConfig):
        """
        Initialize the IPC client with the given configuration.
        """
        self.config = config
        self.reader = None
        self.writer = None

    async def start(self):
        log.debug(f"Connecting to IPC server at {self.config.host}:{self.config.port}")
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.config.host,
                self.config.port,
                limit=MESSAGE_SIZE_LIMIT,
            )
            return True
        except (ConnectionError, OSError, ConnectionRefusedError) as err:
            log.error(f"Can't connect to the Pythagora VSCode extension: {err}")
            return False

    async def _send(self, type: MessageType, **kwargs):
        msg = Message(type=type, **kwargs)
        data = msg.to_bytes()
        if self.writer.is_closing():
            log.error("IPC connection closed, can't send the message")
            raise UIClosedError()
        try:
            self.writer.write(len(data).to_bytes(4, byteorder="big"))
            self.writer.write(data)
            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError) as err:
            log.error(f"Connection lost while sending the message: {err}")
            raise UIClosedError()

    async def _receive(self) -> Message:
        data = b""
        while True:
            try:
                response = await self.reader.read(MESSAGE_SIZE_LIMIT)
            except (
                asyncio.exceptions.IncompleteReadError,
                ConnectionResetError,
                asyncio.exceptions.CancelledError,
                BrokenPipeError,
            ):
                raise UIClosedError()

            if response == b"":
                # We're at EOF, the server closed the connection
                raise UIClosedError()

            data += response
            try:
                return Message.from_bytes(data)
            except ValidationError as err:
                # Incorrect payload is most likely a bug in the server, ignore the message
                log.error(f"Error parsing incoming message: {err}", exc_info=True)
                data = b""
                continue
            except ValueError:
                # Most likely, this is as an incomplete message from the server, wait a bit more
                continue

    async def stop(self):
        if not self.writer:
            return

        log.debug(f"Closing the IPC connection to {self.config.host}:{self.config.port}")

        try:
            await self._send(MessageType.EXIT)
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as err:
            log.error(f"Error while closing the connection: {err}", exc_info=True)

        self.writer = None
        self.reader = None

    async def send_stream_chunk(self, chunk: Optional[str], *, source: Optional[UISource] = None):
        if not self.writer:
            return

        if chunk is None:
            chunk = "\n"  # end of stream

        await self._send(
            MessageType.STREAM,
            content=chunk,
            category=source.type_name if source else None,
        )

    async def send_message(self, message: str, *, source: Optional[UISource] = None):
        if not self.writer:
            return

        log.debug(f"Sending message: [{message.strip()}] from {source.type_name if source else '(none)'}")
        await self._send(
            MessageType.VERBOSE,
            content=message,
            category=source.type_name if source else None,
        )

    async def send_key_expired(self, message: Optional[str] = None):
        await self._send(MessageType.KEY_EXPIRED)

    async def send_app_finished(
        self,
        app_id: Optional[str] = None,
        app_name: Optional[str] = None,
        folder_name: Optional[str] = None,
    ):
        await self._send(
            MessageType.APP_FINISHED,
            content={
                "app_id": app_id,
                "app_name": app_name,
                "folder_name": folder_name,
            },
        )

    async def send_feature_finished(
        self,
        app_id: Optional[str] = None,
        app_name: Optional[str] = None,
        folder_name: Optional[str] = None,
    ):
        await self._send(
            MessageType.FEATURE_FINISHED,
            content={
                "app_id": app_id,
                "app_name": app_name,
                "folder_name": folder_name,
            },
        )

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
        if not self.writer:
            raise UIClosedError()

        category = source.type_name if source else None

        if hint:
            await self._send(MessageType.HINT, content=hint, category=category)
        else:
            await self._send(MessageType.VERBOSE, content=question, category=category)

        await self._send(MessageType.USER_INPUT_REQUEST, content=question, category=category)
        if buttons:
            buttons_str = "/".join(buttons.values())
            if buttons_only:
                await self._send(MessageType.BUTTONS_ONLY, content=buttons_str, category=category)
            else:
                await self._send(MessageType.BUTTONS, content=buttons_str, category=category)
        if initial_text:
            # FIXME: add this to base and console and document it after merging with hint PR
            await self._send(MessageType.INPUT_PREFILL, content=initial_text, category=category)

        response = await self._receive()
        answer = response.content.strip()
        if not answer and default:
            answer = default

        if buttons:
            # Answer matches one of the buttons (or maybe the default if it's a button name)
            if answer in buttons:
                return UserInput(button=answer, text=None)
            # VSCode extension only deals with values so we need to check them as well
            value2key = {v: k for k, v in buttons.items()}
            if answer in value2key:
                return UserInput(button=value2key[answer], text=None)

        if answer or allow_empty:
            return UserInput(button=None, text=answer)

        # Empty answer which we don't allow, treat as user cancelled the input
        return UserInput(cancelled=True)

    async def send_project_stage(self, stage: ProjectStage):
        await self._send(MessageType.INFO, content=json.dumps({"project_stage": stage.value}))

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
        await self._send(
            MessageType.PROGRESS,
            content={
                "task": {
                    "index": index,
                    "num_of_tasks": n_tasks,
                    "description": description,
                    "source": source,
                    "status": status,
                    "source_index": source_index,
                },
                "all_tasks": tasks,
            },
        )

    async def send_modified_files(
        self,
        modified_files: dict[str, str, str],
    ):
        await self._send(
            MessageType.MODIFIED_FILES,
            content={"files": modified_files},
        )

    async def send_step_progress(
        self,
        index: int,
        n_steps: int,
        step: dict,
        task_source: str,
    ):
        await self._send(
            MessageType.PROGRESS,
            content={
                "step": {
                    "index": index,
                    "num_of_steps": n_steps,
                    "step": step,
                    "source": task_source,
                }
            },
        )

    async def send_data_about_logs(
        self,
        data_about_logs: dict,
    ):
        await self._send(
            MessageType.DEBUGGING_LOGS,
            content=data_about_logs,
        )

    async def send_run_command(self, run_command: str):
        await self._send(
            MessageType.RUN_COMMAND,
            content=run_command,
        )

    async def open_editor(self, file: str, line: Optional[int] = None):
        await self._send(
            MessageType.OPEN_FILE,
            content={
                "path": file,  # we assume it's a full path, read the rant in HumanInput.input_required()
                "line": line,
            },
        )

    async def send_project_root(self, path: str):
        await self._send(
            MessageType.PROJECT_FOLDER_NAME,
            content=basename(path),
        )

    async def start_important_stream(self):
        await self._send(
            MessageType.IMPORTANT_STREAM,
            content={},
        )

    async def send_project_stats(self, stats: dict):
        await self._send(
            MessageType.PROJECT_STATS,
            content=stats,
        )

    async def generate_diff(self, file_old: str, file_new: str):
        await self._send(
            MessageType.GENERATE_DIFF,
            content={
                "file_old": file_old,
                "file_new": file_new,
            },
        )

    async def close_diff(self):
        log.debug("Sending signal to close the generated diff file")
        await self._send(MessageType.CLOSE_DIFF)

    async def loading_finished(self):
        log.debug("Sending project loading finished signal to the extension")
        await self._send(MessageType.LOADING_FINISHED)

    async def send_project_description(self, description: str):
        await self._send(MessageType.PROJECT_DESCRIPTION, content={"project_description": description})

    async def send_features_list(self, features: list[str]):
        await self._send(MessageType.FEATURES_LIST, content={"featuresList": features})

    async def import_project(self, project_dir: str):
        await self._send(MessageType.IMPORT_PROJECT, content={"project_dir": project_dir})


__all__ = ["IPCClientUI"]
