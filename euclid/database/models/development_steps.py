from peewee import *

from playhouse.postgres_ext import BinaryJSONField

from database.models.components.base_models import BaseModel
from database.models.app import App


class DevelopmentSteps(BaseModel):
    app = ForeignKeyField(App, primary_key=True)
    hash_id = CharField(unique=True, null=False)
    messages = BinaryJSONField(null=True)

    class Meta:
        db_table = 'development_steps'