from peewee import *
from datetime import datetime
from uuid import uuid4

from const import db


# Establish connection to the database
database = PostgresqlDatabase(
    db.DB_NAME,
    user=db.DB_USER,
    password=db.DB_PASSWORD,
    host=db.DB_HOST,
    port=db.DB_PORT
)


class BaseModel(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = database
