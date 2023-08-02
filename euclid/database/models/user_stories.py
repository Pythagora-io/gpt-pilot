from peewee import *

from database.models.components.progress_step import ProgressStep


class UserStories(ProgressStep):
    user_stories = TextField()
    class Meta:
        db_table = 'user_stories'
