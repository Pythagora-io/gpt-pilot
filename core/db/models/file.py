from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.models import Base

if TYPE_CHECKING:
    from core.db.models import FileContent, ProjectState


class File(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("project_state_id", "path"),)

    # ID and parent FKs
    id: Mapped[int] = mapped_column(primary_key=True)
    project_state_id: Mapped[UUID] = mapped_column(ForeignKey("project_states.id", ondelete="CASCADE"))
    content_id: Mapped[str] = mapped_column(ForeignKey("file_contents.id", ondelete="RESTRICT"))

    # Attributes
    path: Mapped[str] = mapped_column()
    meta: Mapped[dict] = mapped_column(default=dict, server_default="{}")

    # Relationships
    project_state: Mapped[Optional["ProjectState"]] = relationship(back_populates="files", lazy="raise")
    content: Mapped["FileContent"] = relationship(back_populates="files", lazy="selectin")

    def clone(self) -> "File":
        """
        Clone the file object, to be used in a new project state.

        The clone references the same file content object as the original.

        :return: The cloned file object.
        """
        return File(
            project_state=None,
            content_id=self.content_id,
            path=self.path,
            meta=self.meta,
        )
