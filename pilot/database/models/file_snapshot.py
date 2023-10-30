import logging

from peewee import ForeignKeyField, BlobField

from database.models.components.base_models import BaseModel
from database.models.development_steps import DevelopmentSteps
from database.models.app import App
from database.models.files import File

log = logging.getLogger(__name__)


class SmartBlobField(BlobField):
    """
    A binary blob field that can also accept/return utf-8 strings.

    This is a temporary workaround for the fact that we're passing either binary
    or string contents to the database. Once this is cleaned up, we should only
    accept binary content and explcitily convert from/to strings as needed.
    """

    def db_value(self, value):
        if isinstance(value, str):
            log.warning("FileSnapshot content is a string, expected bytes, working around it.")
            value = value.encode("utf-8")
        return super().db_value(value)

    def python_value(self, value):
        val = bytes(super().python_value(value))
        try:
            return val.decode("utf-8")
        except UnicodeDecodeError:
            return val


class FileSnapshot(BaseModel):
    app = ForeignKeyField(App, on_delete='CASCADE')
    development_step = ForeignKeyField(DevelopmentSteps, backref='files', on_delete='CASCADE')
    file = ForeignKeyField(File, on_delete='CASCADE', null=True)
    content = SmartBlobField()

    class Meta:
        table_name = 'file_snapshot'
        indexes = (
            (('development_step', 'file'), True),
        )
