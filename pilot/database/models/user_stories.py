from peewee import *

from database.models.components.progress_step import ProgressStep
from playhouse.postgres_ext import BinaryJSONField


class UserStories(ProgressStep):
    user_stories = BinaryJSONField()
    class Meta:
        db_table = 'user_stories'
