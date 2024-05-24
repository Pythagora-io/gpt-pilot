# DeclarativeBase enables declarative configuration of
# database models within SQLAlchemy.
#
# It also sets up a registry for the classes that inherit from it,
# so that SQLAlechemy understands how they map to database tables.

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQL database models."""

    # Mapping of Python types to SQLAlchemy types.
    type_annotation_map = {
        list[dict]: JSON,
        list[str]: JSON,
        dict: JSON,
    }

    metadata = MetaData(
        # Naming conventions for constraints, foreign keys, etc.
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
