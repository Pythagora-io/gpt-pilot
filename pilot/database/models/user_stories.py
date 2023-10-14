from database.config import DATABASE_TYPE
from database.models.components.progress_step import ProgressStep
from database.models.components.sqlite_middlewares import JSONField
from playhouse.postgres_ext import BinaryJSONField


class UserStories(ProgressStep):
    if DATABASE_TYPE == 'postgres':
        user_stories = BinaryJSONField()
    else:
        user_stories = JSONField()  # Custom JSON field for SQLite
    class Meta:
        table_name = 'user_stories'
