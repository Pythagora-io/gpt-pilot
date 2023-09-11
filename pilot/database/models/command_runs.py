from peewee import *

from database.models.components.base_models import BaseModel
from database.models.app import App


class CommandRuns(BaseModel):
    id = AutoField()
    app = ForeignKeyField(App, on_delete='CASCADE')
    hash_id = CharField(null=False)
    command = TextField(null=True)
    cli_response = TextField(null=True)
    previous_step = ForeignKeyField('self', null=True, column_name='previous_step')

    class Meta:
        db_table = 'command_runs'
        indexes = (
            (('app', 'hash_id'), True),
        )