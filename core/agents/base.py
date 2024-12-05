from typing import Any, Callable, Optional

from core.agents.response import AgentResponse
from core.config import get_config
from core.db.models import ProjectState
from core.llm.base import BaseLLMClient, LLMError
from core.log import get_logger
from core.proc.process_manager import ProcessManager
from core.state.state_manager import StateManager
from core.ui.base import AgentSource, UIBase, UserInput, pythagora_source

log = get_logger(__name__)


class BaseAgent:
    """
    Base class for agents.
    """

    agent_type: str
    display_name: str

    def __init__(
        self,
        state_manager: StateManager,
        ui: UIBase,
        *,
        step: Optional[Any] = None,
        prev_response: Optional["AgentResponse"] = None,
        process_manager: Optional["ProcessManager"] = None,
        data: Optional[Any] = None,
        args: Optional[Any] = None,
    ):
        """
        Create a new agent.
        """
        self.ui_source = AgentSource(self.display_name, self.agent_type)
        self.ui = ui
        self.state_manager = state_manager
        self.process_manager = process_manager
        self.prev_response = prev_response
        self.step = step
        self.data = data
        self.args = args

    @property
    def current_state(self) -> ProjectState:
        """Current state of the project (read-only)."""
        return self.state_manager.current_state

    @property
    def next_state(self) -> ProjectState:
        """Next state of the project (write-only)."""
        return self.state_manager.next_state

    async def send_message(self, message: str, extra_info: Optional[str] = None):
        """
        Send a message to the user.

        Convenience method, uses `UIBase.send_message()` to send the message,
        setting the correct source and project state ID.

        :param message: Message to send.
        :param extra_info: Extra information to indicate special functionality in extension
        """
        await self.ui.send_message(
            message + "\n", source=self.ui_source, project_state_id=str(self.current_state.id), extra_info=extra_info
        )

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
        extra_info: Optional[str] = None,
        placeholder: Optional[str] = None,
    ) -> UserInput:
        """
        Ask a question to the user and return the response.

        Convenience method, uses `UIBase.ask_question()` to
        ask the question, setting the correct source and project state ID, and
        logging the question/response.

        :param question: Question to ask.
        :param buttons: Buttons to display with the question.
        :param default: Default button to select.
        :param buttons_only: Only display buttons, no text input.
        :param allow_empty: Allow empty input.
        :param full_screen: Show question full screen in extension.
        :param hint: Text to display in a popup as a hint to the question.
        :param verbose: Whether to log the question and response.
        :param initial_text: Initial text input.
        :param extra_info: Extra information to indicate special functionality in extension.
        :param placeholder: Placeholder text for the input field.
        :return: User response.
        """
        response = await self.ui.ask_question(
            question,
            buttons=buttons,
            default=default,
            buttons_only=buttons_only,
            allow_empty=allow_empty,
            full_screen=full_screen,
            hint=hint,
            verbose=verbose,
            initial_text=initial_text,
            source=self.ui_source,
            project_state_id=str(self.current_state.id),
            extra_info=extra_info,
            placeholder=placeholder,
        )
        await self.state_manager.log_user_input(question, response)
        return response

    async def stream_handler(self, content: str):
        """
        Handle streamed response from the LLM.

        Serves as a callback to `AgentBase.llm()` so it can stream the responses to the UI.

        :param content: Response content.
        """

        await self.ui.send_stream_chunk(content, source=self.ui_source, project_state_id=str(self.current_state.id))

        if content is None:
            await self.ui.send_message("", source=self.ui_source, project_state_id=str(self.current_state.id))

    async def error_handler(self, error: LLMError, message: Optional[str] = None) -> bool:
        """
        Handle error responses from the LLM.

        :param error: The exception that was thrown the the LLM client.
        :param message: Optional message to show.
        :return: Whether the request should be retried.
        """

        if error == LLMError.KEY_EXPIRED:
            await self.ui.send_key_expired(message)
            answer = await self.ask_question(
                "Would you like to retry the last step?",
                buttons={"yes": "Yes", "no": "No"},
                buttons_only=True,
            )
            if answer.button == "yes":
                return True
        elif error == LLMError.GENERIC_API_ERROR:
            await self.stream_handler(message)
            answer = await self.ui.ask_question(
                "Would you like to retry the failed request?",
                buttons={"yes": "Yes", "no": "No"},
                buttons_only=True,
                source=pythagora_source,
            )
            if answer.button == "yes":
                return True
        elif error == LLMError.RATE_LIMITED:
            await self.stream_handler(message)

        return False

    def get_llm(self, name=None, stream_output=False) -> Callable:
        """
        Get a new instance of the agent-specific LLM client.

        The client initializes the UI stream handler and stores the
        request/response to the current state's log. The agent name
        can be overridden in case the agent needs to use a different
        model configuration.

        :param name: Name of the agent for configuration (default: class name).
        :return: LLM client for the agent.
        """

        if name is None:
            name = self.__class__.__name__

        config = get_config()

        llm_config = config.llm_for_agent(name)
        client_class = BaseLLMClient.for_provider(llm_config.provider)
        stream_handler = self.stream_handler if stream_output else None
        llm_client = client_class(llm_config, stream_handler=stream_handler, error_handler=self.error_handler)

        async def client(convo, **kwargs) -> Any:
            """
            Agent-specific LLM client.

            For details on optional arguments to pass to the LLM client,
            see `pythagora.llm.openai_client.OpenAIClient()`.
            """
            response, request_log = await llm_client(convo, **kwargs)
            await self.state_manager.log_llm_request(request_log, agent=self)
            return response

        return client

    async def run() -> AgentResponse:
        """
        Run the agent.

        :return: Response from the agent.
        """
        raise NotImplementedError()
