from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.db.models import Base
from core.proc.exec_log import ExecLog as ExecLogData

if TYPE_CHECKING:
    from core.db.models import Branch, ProjectState


class ExecLog(Base):
    __tablename__ = "exec_logs"

    # ID and parent FKs
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"))
    project_state_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("project_states.id", ondelete="SET NULL"))

    # Attributes
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    duration: Mapped[float] = mapped_column()
    cmd: Mapped[str] = mapped_column()
    cwd: Mapped[str] = mapped_column()
    env: Mapped[dict] = mapped_column()
    timeout: Mapped[Optional[float]] = mapped_column()
    status_code: Mapped[Optional[int]] = mapped_column()
    stdout: Mapped[str] = mapped_column()
    stderr: Mapped[str] = mapped_column()
    analysis: Mapped[str] = mapped_column()
    success: Mapped[bool] = mapped_column()

    # Relationships
    branch: Mapped["Branch"] = relationship(back_populates="exec_logs", lazy="raise")
    project_state: Mapped["ProjectState"] = relationship(back_populates="exec_logs", lazy="raise")

    @classmethod
    def from_exec_log(cls, project_state: "ProjectState", exec_log: ExecLogData) -> "ExecLog":
        """
        Store the user input in the database.

        Note this just creates the UserInput object. It is committed to the
        database only when the DB session itself is comitted.

        :param project_state: Project state to associate the request log with.
        :param question: Question the user was asked.
        :param user_input: User input.
        :return: Newly created User input in the database.
        """
        session = inspect(project_state).async_session

        obj = cls(
            project_state=project_state,
            branch=project_state.branch,
            started_at=exec_log.started_at,
            duration=exec_log.duration,
            cmd=exec_log.cmd,
            cwd=exec_log.cwd,
            env=exec_log.env,
            timeout=exec_log.timeout,
            status_code=exec_log.status_code,
            stdout=exec_log.stdout,
            stderr=exec_log.stderr,
            analysis=exec_log.analysis,
            success=exec_log.success,
        )
        session.add(obj)
        return obj
