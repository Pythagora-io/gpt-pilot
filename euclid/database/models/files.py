from peewee import *

from database.models.components.base_models import BaseModel
from database.models.development_steps import DevelopmentSteps
from database.models.app import App

class File(BaseModel):
    app = ForeignKeyField(App)
    name = CharField()
    path = CharField()
    description = TextField()

    class Meta:
        indexes = (
            (('app', 'name', 'path'), True),
        )