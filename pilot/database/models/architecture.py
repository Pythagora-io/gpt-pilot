from peewee import *

from database.models.components.progress_step import ProgressStep
from playhouse.postgres_ext import BinaryJSONField


class Architecture(ProgressStep):
    architecture = BinaryJSONField()
    class Meta:
        db_table = 'architecture'
