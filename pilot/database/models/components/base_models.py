from peewee import Model, UUIDField, DateTimeField
from datetime import datetime
from uuid import uuid4

from database.config import DATABASE_TYPE
from database.connection.postgres import get_postgres_database
from database.connection.sqlite import get_sqlite_database


# Establish connection to the database
if DATABASE_TYPE == "postgres":
    database = get_postgres_database()
else:
    database = get_sqlite_database()


class BaseModel(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = database
