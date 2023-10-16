from peewee import AutoField, CharField, TextField, ForeignKeyField

from database.models.components.base_models import BaseModel
from database.models.app import App


class File(BaseModel):
    id = AutoField()
    app = ForeignKeyField(App, on_delete='CASCADE')
    name = CharField()
    path = CharField()
    full_path = CharField()
    description = TextField(null=True)

    class Meta:
        indexes = (
            (('app', 'name', 'path'), True),
        )
