from peewee import *

from database.models.components.base_models import BaseModel
from database.models.development_steps import DevelopmentSteps
from database.models.app import App
from database.models.files import File

class FileSnapshot(BaseModel):
    app = ForeignKeyField(App, on_delete='CASCADE')
    development_step = ForeignKeyField(DevelopmentSteps, backref='files', on_delete='CASCADE')
    file = ForeignKeyField(File, on_delete='CASCADE', null=True)
    content = TextField()

    class Meta:
        db_table = 'file_snapshot'
        indexes = (
            (('development_step', 'file'), True),
        )