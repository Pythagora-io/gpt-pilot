from peewee import *

from database.models.components.base_models import BaseModel
from database.models.user import User


class App(BaseModel):
    user = ForeignKeyField(User, backref='apps')
    app_type = CharField()
    status = CharField(default='started')