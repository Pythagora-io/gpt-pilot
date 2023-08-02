from peewee import *

from database.models.components.progress_step import ProgressStep


class Architecture(ProgressStep):
    architecture = TextField()
    class Meta:
        db_table = 'architecture'
