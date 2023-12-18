from peewee import ForeignKeyField, CharField, BooleanField, DateTimeField
from database.config import DATABASE_TYPE
from database.models.components.base_models import BaseModel
from database.models.app import App
from database.models.development_steps import DevelopmentSteps
from database.models.components.sqlite_middlewares import JSONField
from playhouse.postgres_ext import BinaryJSONField


class Feature(BaseModel):
    app = ForeignKeyField(App, backref='feature', on_delete='CASCADE')
    summary = CharField()

    if DATABASE_TYPE == 'postgres':
        messages = BinaryJSONField(null=True)
    else:
        messages = JSONField(null=True)

    previous_step = ForeignKeyField(DevelopmentSteps, column_name='previous_step')
    completed = BooleanField(default=False)
    completed_at = DateTimeField(null=True)
