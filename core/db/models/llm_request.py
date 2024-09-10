from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.db.models import Base
from core.llm.request_log import LLMRequestLog

if TYPE_CHECKING:
    from core.agents.base import BaseAgent
    from core.db.models import Branch, ProjectState


class LLMRequest(Base):
    __tablename__ = "llm_requests"

    # ID and parent FKs
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"))
    project_state_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("project_states.id", ondelete="SET NULL"))

    # Attributes
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    agent: Mapped[Optional[str]] = mapped_column()
    provider: Mapped[str] = mapped_column()
    model: Mapped[str] = mapped_column()
    temperature: Mapped[float] = mapped_column()
    messages: Mapped[list[dict]] = mapped_column()
    prompts: Mapped[list[str]] = mapped_column(server_default="[]")
    response: Mapped[Optional[str]] = mapped_column()
    prompt_tokens: Mapped[int] = mapped_column()
    completion_tokens: Mapped[int] = mapped_column()
    duration: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column()
    error: Mapped[Optional[str]] = mapped_column()

    # Relationships
    branch: Mapped["Branch"] = relationship(back_populates="llm_requests", lazy="raise")
    project_state: Mapped["ProjectState"] = relationship(back_populates="llm_requests", lazy="raise")

    @classmethod
    def from_request_log(
        cls,
        project_state: "ProjectState",
        agent: Optional["BaseAgent"],
        request_log: LLMRequestLog,
    ) -> "LLMRequest":
        """
        Store the request log in the database.

        Note this just creates the request log object. It is committed to the
        database only when the DB session itself is comitted.

        :param project_state: Project state to associate the request log with.
        :param agent: Agent that made the request (if the caller was an agent).
        :param request_log: Request log.
        :return: Newly created LLM request log in the database.
        """
        session: AsyncSession = inspect(project_state).async_session

        obj = cls(
            project_state=project_state,
            branch=project_state.branch,
            agent=agent.agent_type,
            provider=request_log.provider,
            model=request_log.model,
            temperature=request_log.temperature,
            messages=request_log.messages,
            prompts=request_log.prompts,
            response=request_log.response,
            prompt_tokens=request_log.prompt_tokens,
            completion_tokens=request_log.completion_tokens,
            duration=request_log.duration,
            status=request_log.status,
            error=request_log.error,
        )
        session.add(obj)
        return obj
