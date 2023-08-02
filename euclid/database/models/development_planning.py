from peewee import *

from database.models.components.progress_step import ProgressStep


class DevelopmentPlanning(ProgressStep):
    architecture = TextField()

    class Meta:
        db_table = 'development_planning'
