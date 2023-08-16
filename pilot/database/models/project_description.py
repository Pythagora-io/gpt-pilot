from peewee import *

from playhouse.postgres_ext import BinaryJSONField

from database.models.components.progress_step import ProgressStep


class ProjectDescription(ProgressStep):
    prompt = TextField()
    summary = TextField()

    class Meta:
        db_table = 'project_description'
