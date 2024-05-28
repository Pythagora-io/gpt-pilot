from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, inspect, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.db.models import Base

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from core.db.models import ExecLog, LLMRequest, Project, ProjectState, UserInput


class Branch(Base):
    __tablename__ = "branches"

    DEFAULT = "main"

    # ID and parent FKs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    # Attributes
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    name: Mapped[str] = mapped_column(default=DEFAULT)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="branches", lazy="selectin")
    states: Mapped[list["ProjectState"]] = relationship(back_populates="branch", cascade="all", lazy="raise")
    llm_requests: Mapped[list["LLMRequest"]] = relationship(back_populates="branch", cascade="all", lazy="raise")
    user_inputs: Mapped[list["UserInput"]] = relationship(back_populates="branch", cascade="all", lazy="raise")
    exec_logs: Mapped[list["ExecLog"]] = relationship(back_populates="branch", cascade="all", lazy="raise")

    @staticmethod
    async def get_by_id(session: "AsyncSession", branch_id: Union[str, UUID]) -> Optional["Branch"]:
        """
        Get a project by ID.

        :param session: The SQLAlchemy session.
        :param project_id: The branch ID (as str or UUID value).
        :return: The Branch object if found, None otherwise.
        """
        if not isinstance(branch_id, UUID):
            branch_id = UUID(branch_id)

        result = await session.execute(select(Branch).where(Branch.id == branch_id))
        return result.scalar_one_or_none()

    async def get_last_state(self) -> Optional["ProjectState"]:
        """
        Get the last project state of the branch.

        :return: The last step of the branch, or None if there are no steps.
        """

        from core.db.models import ProjectState

        session = inspect(self).async_session
        if session is None:
            raise ValueError("Branch instance not associated with a DB session.")

        result = await session.execute(
            select(ProjectState)
            .where(ProjectState.branch_id == self.id)
            .order_by(ProjectState.step_index.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_state_at_step(self, step_index: int) -> Optional["ProjectState"]:
        """
        Get the project state at the given step index for the branch.

        :return: The indicated step within the branch, or None if there's no such step.
        """

        from core.db.models import ProjectState

        session = inspect(self).async_session
        if session is None:
            raise ValueError("Branch instance not associated with a DB session.")

        result = await session.execute(
            select(ProjectState).where((ProjectState.branch_id == self.id) & (ProjectState.step_index == step_index))
        )
        return result.scalar_one_or_none()
