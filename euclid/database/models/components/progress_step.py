from peewee import *

from playhouse.postgres_ext import BinaryJSONField

from database.models.components.base_models import BaseModel
from database.models.app import App


class ProgressStep(BaseModel):
    app = ForeignKeyField(App, primary_key=True)
    step = CharField()
    data = BinaryJSONField(null=True)
    messages = BinaryJSONField(null=True)
    app_data = BinaryJSONField()
    completed = BooleanField(default=False)
    completed_at = DateTimeField(null=True)
