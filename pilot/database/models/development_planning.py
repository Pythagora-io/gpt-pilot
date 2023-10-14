from database.config import DATABASE_TYPE
from database.models.components.progress_step import ProgressStep
from database.models.components.sqlite_middlewares import JSONField
from playhouse.postgres_ext import BinaryJSONField


class DevelopmentPlanning(ProgressStep):
    if DATABASE_TYPE == 'postgres':
        development_plan = BinaryJSONField()
    else:
        development_plan = JSONField()  # Custom JSON field for SQLite

    class Meta:
        table_name = 'development_planning'
