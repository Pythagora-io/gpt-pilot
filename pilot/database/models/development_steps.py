from peewee import ForeignKeyField, AutoField, TextField, IntegerField, CharField
from database.config import DATABASE_TYPE
from database.models.components.base_models import BaseModel
from database.models.app import App
from database.models.components.sqlite_middlewares import JSONField
from playhouse.postgres_ext import BinaryJSONField


class DevelopmentSteps(BaseModel):
    id = AutoField()  # This will serve as the primary key
    app = ForeignKeyField(App, on_delete='CASCADE')
    prompt_path = TextField(null=True)
    llm_req_num = IntegerField(null=True)
    token_limit_exception_raised = TextField(null=True)

    if DATABASE_TYPE == 'postgres':
        messages = BinaryJSONField(null=True)
        llm_response = BinaryJSONField(null=False)
        prompt_data = BinaryJSONField(null=True)
    else:
        messages = JSONField(null=True)  # Custom JSON field for SQLite
        llm_response = JSONField(null=False)  # Custom JSON field for SQLite
        prompt_data = JSONField(null=True)

    previous_step = ForeignKeyField('self', null=True, column_name='previous_step')
    high_level_step = CharField(null=True)

    class Meta:
        table_name = 'development_steps'
        indexes = (
            (('app', 'previous_step', 'high_level_step'), True),
        )
