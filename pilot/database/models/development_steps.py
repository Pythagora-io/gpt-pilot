from peewee import *
from database.config import DATABASE_TYPE
from database.models.components.base_models import BaseModel
from database.models.app import App
from database.models.components.sqlite_middlewares import JSONField
from playhouse.postgres_ext import BinaryJSONField

class DevelopmentSteps(BaseModel):
    id = AutoField()  # This will serve as the primary key
    app = ForeignKeyField(App, on_delete='CASCADE')
    hash_id = CharField(null=False)

    if DATABASE_TYPE == 'postgres':
        messages = BinaryJSONField(null=True)
        llm_response = BinaryJSONField(null=False)
    else:
        messages = JSONField(null=True)  # Custom JSON field for SQLite
        llm_response = JSONField(null=False)  # Custom JSON field for SQLite

    previous_step = ForeignKeyField('self', null=True, column_name='previous_step')

    class Meta:
        db_table = 'development_steps'
        indexes = (
            (('app', 'hash_id'), True),
        )
