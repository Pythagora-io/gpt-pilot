from peewee import *

from database.models.components.base_models import BaseModel
from database.models.development_steps import DevelopmentSteps

class FileSnapshot(BaseModel):
    development_step = ForeignKeyField(DevelopmentSteps, backref='files', on_delete='CASCADE')
    name = CharField()
    content = TextField()

    class Meta:
        db_table = 'file_snapshot'
        indexes = (
            (('development_step', 'name'), True),
        )