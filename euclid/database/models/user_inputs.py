from peewee import *

from database.models.components.base_models import BaseModel
from database.models.app import App


class UserInputs(BaseModel):
    id = AutoField()
    app = ForeignKeyField(App)
    hash_id = CharField(null=False)
    query = TextField(null=True)
    user_input = TextField(null=True)

    class Meta:
        db_table = 'user_inputs'
        indexes = (
            (('app', 'hash_id'), True),
        )