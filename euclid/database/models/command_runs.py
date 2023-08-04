from peewee import *

from database.models.components.base_models import BaseModel
from database.models.app import App


class CommandRuns(BaseModel):
    id = AutoField()
    app = ForeignKeyField(App)
    hash_id = CharField(null=False)
    command = TextField(null=True)
    cli_response = TextField(null=True)

    class Meta:
        db_table = 'command_runs'
        indexes = (
            (('app', 'hash_id'), True),
        )