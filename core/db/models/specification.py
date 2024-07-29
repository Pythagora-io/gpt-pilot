from copy import deepcopy
from typing import TYPE_CHECKING, Optional

from sqlalchemy import delete, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.models import Base

if TYPE_CHECKING:
    from core.db.models import ProjectState


class Complexity:
    """Estimate of the project or feature complexity."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    HARD = "hard"


class Specification(Base):
    __tablename__ = "specifications"

    # ID and parent FKs
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Attributes
    original_description: Mapped[Optional[str]] = mapped_column()
    description: Mapped[str] = mapped_column(default="")
    template_summary: Mapped[Optional[str]] = mapped_column()
    architecture: Mapped[str] = mapped_column(default="")
    system_dependencies: Mapped[list[dict]] = mapped_column(default=list)
    package_dependencies: Mapped[list[dict]] = mapped_column(default=list)
    templates: Mapped[Optional[dict]] = mapped_column()

    complexity: Mapped[str] = mapped_column(server_default=Complexity.HARD)
    example_project: Mapped[Optional[str]] = mapped_column()

    # Relationships
    project_states: Mapped[list["ProjectState"]] = relationship(back_populates="specification", lazy="raise")

    def clone(self) -> "Specification":
        """
        Clone the specification.
        """
        clone = Specification(
            original_description=self.original_description,
            description=self.description,
            template_summary=self.template_summary,
            architecture=self.architecture,
            system_dependencies=self.system_dependencies,
            package_dependencies=self.package_dependencies,
            templates=deepcopy(self.templates) if self.templates else None,
            complexity=self.complexity,
            example_project=self.example_project,
        )
        return clone

    @classmethod
    async def delete_orphans(cls, session: AsyncSession):
        """
        Delete Specification objects that are not referenced by any ProjectState object.

        :param session: The database session.
        """
        from core.db.models import ProjectState

        await session.execute(
            delete(Specification).where(~Specification.id.in_(select(distinct(ProjectState.specification_id))))
        )
