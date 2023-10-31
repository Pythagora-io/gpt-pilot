from peewee import AutoField, ForeignKeyField, TextField, CharField

from database.models.components.base_models import BaseModel
from database.models.app import App


class UserInputs(BaseModel):
    id = AutoField()
    app = ForeignKeyField(App, on_delete='CASCADE')
    query = TextField(null=True)
    user_input = TextField(null=True)
    hint = TextField(null=True)
    previous_step = ForeignKeyField('self', null=True, column_name='previous_step')
    high_level_step = CharField(null=True)

    class Meta:
        table_name = 'user_inputs'
        indexes = (
            (('app', 'previous_step', 'high_level_step'), True),
        )