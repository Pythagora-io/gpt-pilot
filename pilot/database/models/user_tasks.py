from peewee import *

from database.models.components.progress_step import ProgressStep
from playhouse.postgres_ext import BinaryJSONField


class UserTasks(ProgressStep):
    user_tasks = BinaryJSONField()
    class Meta:
        db_table = 'user_tasks'
