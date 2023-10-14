from peewee import ForeignKeyField, CharField

from database.models.components.base_models import BaseModel
from database.models.user import User


class App(BaseModel):
    user = ForeignKeyField(User, backref='apps')
    app_type = CharField(null=True)
    name = CharField(null=True)
    status = CharField(null=True)