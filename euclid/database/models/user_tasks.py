from peewee import *

from database.models.components.progress_step import ProgressStep


class UserTasks(ProgressStep):
    user_tasks = TextField()
    class Meta:
        db_table = 'user_tasks'
