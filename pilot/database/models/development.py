from peewee import *

from database.models.components.progress_step import ProgressStep


class Development(ProgressStep):
    class Meta:
        db_table = 'development'
