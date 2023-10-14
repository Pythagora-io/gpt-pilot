from peewee import CharField

from database.models.components.base_models import BaseModel


class User(BaseModel):
    email = CharField(unique=True)
    password = CharField()
