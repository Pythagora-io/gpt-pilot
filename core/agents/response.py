from enum import Enum
from typing import TYPE_CHECKING, Optional

from core.log import get_logger

if TYPE_CHECKING:
    from core.agents.base import BaseAgent
    from core.agents.error_handler import ErrorHandler


log = get_logger(__name__)


class ResponseType(str, Enum):
    DONE = "done"
    """Agent has finished processing."""

    ERROR = "error"
    """There was an error processing the request."""

    CANCEL = "cancel"
    """User explicitly cancelled the operation."""

    EXIT = "exit"
    """Pythagora should exit."""

    CODE_REVIEW = "code-review"
    """Agent is requesting a review of the created code."""

    CODE_REVIEW_FEEDBACK = "code-review-feedback"
    """Agent is providing feedback on the code review."""

    DESCRIBE_FILES = "describe-files"
    """Analysis of the files in the project is requested."""

    INPUT_REQUIRED = "input-required"
    """User needs to modify a line in the generated code."""

    TASK_REVIEW_FEEDBACK = "task-review-feedback"
    """Agent is providing feedback on the entire task."""

    IMPORT_PROJECT = "import-project"
    """User wants to import an existing project."""

    EXTERNAL_DOCS_REQUIRED = "external-docs-required"
    """We need to fetch external docs for a task."""

    UPDATE_SPECIFICATION = "update-specification"
    """We need to update the project specification."""


class AgentResponse:
    type: ResponseType = ResponseType.DONE
    agent: "BaseAgent"
    data: Optional[dict]

    def __init__(self, type: ResponseType, agent: "BaseAgent", data: Optional[dict] = None):
        self.type = type
        self.agent = agent
        self.data = data

    def __repr__(self) -> str:
        return f"<AgentResponse type={self.type} agent={self.agent}>"

    @staticmethod
    def done(agent: "BaseAgent") -> "AgentResponse":
        return AgentResponse(type=ResponseType.DONE, agent=agent)

    @staticmethod
    def error(agent: "BaseAgent", message: str, details: Optional[dict] = None) -> "AgentResponse":
        return AgentResponse(
            type=ResponseType.ERROR,
            agent=agent,
            data={"message": message, "details": details},
        )

    @staticmethod
    def cancel(agent: "BaseAgent") -> "AgentResponse":
        return AgentResponse(type=ResponseType.CANCEL, agent=agent)

    @staticmethod
    def exit(agent: "ErrorHandler") -> "AgentResponse":
        return AgentResponse(type=ResponseType.EXIT, agent=agent)

    @staticmethod
    def code_review(
        agent: "BaseAgent",
        path: str,
        instructions: str,
        old_content: str,
        new_content: str,
        attempt: int,
    ) -> "AgentResponse":
        return AgentResponse(
            type=ResponseType.CODE_REVIEW,
            agent=agent,
            data={
                "path": path,
                "instructions": instructions,
                "old_content": old_content,
                "new_content": new_content,
                "attempt": attempt,
            },
        )

    @staticmethod
    def code_review_feedback(
        agent: "BaseAgent",
        new_content: str,
        approved_content: str,
        feedback: str,
        attempt: int,
    ) -> "AgentResponse":
        return AgentResponse(
            type=ResponseType.CODE_REVIEW_FEEDBACK,
            agent=agent,
            data={
                "new_content": new_content,
                "approved_content": approved_content,
                "feedback": feedback,
                "attempt": attempt,
            },
        )

    @staticmethod
    def describe_files(agent: "BaseAgent") -> "AgentResponse":
        return AgentResponse(type=ResponseType.DESCRIBE_FILES, agent=agent)

    @staticmethod
    def input_required(agent: "BaseAgent", files: list[dict[str, int]]) -> "AgentResponse":
        return AgentResponse(type=ResponseType.INPUT_REQUIRED, agent=agent, data={"files": files})

    @staticmethod
    def task_review_feedback(agent: "BaseAgent", feedback: str) -> "AgentResponse":
        return AgentResponse(
            type=ResponseType.TASK_REVIEW_FEEDBACK,
            agent=agent,
            data={
                "feedback": feedback,
            },
        )

    @staticmethod
    def import_project(agent: "BaseAgent") -> "AgentResponse":
        return AgentResponse(type=ResponseType.IMPORT_PROJECT, agent=agent)

    @staticmethod
    def external_docs_required(agent: "BaseAgent") -> "AgentResponse":
        return AgentResponse(type=ResponseType.EXTERNAL_DOCS_REQUIRED, agent=agent)

    @staticmethod
    def update_specification(agent: "BaseAgent", description: str) -> "AgentResponse":
        return AgentResponse(
            type=ResponseType.UPDATE_SPECIFICATION,
            agent=agent,
            data={
                "description": description,
            },
        )
