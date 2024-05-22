from typing import TYPE_CHECKING, Optional

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
    description: Mapped[str] = mapped_column(default="")
    architecture: Mapped[str] = mapped_column(default="")
    system_dependencies: Mapped[list[dict]] = mapped_column(default=list)
    package_dependencies: Mapped[list[dict]] = mapped_column(default=list)
    template: Mapped[Optional[str]] = mapped_column()
    complexity: Mapped[str] = mapped_column(server_default=Complexity.HARD)

    # Relationships
    project_states: Mapped[list["ProjectState"]] = relationship(back_populates="specification")

    def clone(self) -> "Specification":
        """
        Clone the specification.
        """
        clone = Specification(
            description=self.description,
            architecture=self.architecture,
            system_dependencies=self.system_dependencies,
            package_dependencies=self.package_dependencies,
            template=self.template,
            complexity=self.complexity,
        )
        return clone
