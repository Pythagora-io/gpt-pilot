from playhouse.shortcuts import model_to_dict
from peewee import *

from utils.utils import hash_data
from database.models.components.base_models import database
from database.models.user import User
from database.models.app import App
from database.models.project_description import ProjectDescription
from database.models.user_stories import UserStories
from database.models.user_tasks import UserTasks
from database.models.architecture import Architecture
from database.models.development_planning import DevelopmentPlanning
from database.models.development_steps import DevelopmentSteps
from database.models.environment_setup import EnvironmentSetup
from database.models.development import Development


def save_user(user_id, email="email", password="password"):
    try:
        user = User.get(User.id == user_id)
        return user
    except DoesNotExist:
        return User.create(id=user_id, email=email, password=password)


def save_app(user_id, app_id, app_type):
    try:
        app = App.get(App.id == app_id)
    except DoesNotExist:
        user = save_user(user_id)
        app = App.create(id=app_id, user=user, app_type=app_type)

    return app


def save_progress(app_id, step, data):
    progress_table_map = {
        'project_description': ProjectDescription,
        'user_stories': UserStories,
        'user_tasks': UserTasks,
        'architecture': Architecture,
        'development_planning': DevelopmentPlanning,
        'environment_setup': EnvironmentSetup,
        'development': Development,
    }

    data['step'] = step

    ProgressTable = progress_table_map.get(step)
    if not ProgressTable:
        raise ValueError(f"Invalid step: {step}")

    app = get_app(app_id)

    # Use the get_or_create method, which attempts to retrieve a record
    # or creates a new one if it does not exist.
    progress, created = ProgressTable.get_or_create(app=app, defaults=data)

    # If the record was not created, it already existed and we should update it
    if not created:
        for key, value in data.items():
            setattr(progress, key, value)
        progress.save()

    return progress


def get_app(app_id):
    try:
        app = App.get(App.id == app_id)
        return app
    except DoesNotExist:
        raise ValueError(f"No app with id: {app_id}")


def get_progress_steps(app_id, step=None):
    progress_table_map = {
        'project_description': ProjectDescription,
        'user_stories': UserStories,
        'user_tasks': UserTasks,
        'architecture': Architecture,
        'development_planning': DevelopmentPlanning,
        'environment_setup': EnvironmentSetup,
        'development': Development,
    }

    if step:
        ProgressTable = progress_table_map.get(step)
        if not ProgressTable:
            raise ValueError(f"Invalid step: {step}")

        try:
            progress = ProgressTable.get(ProgressTable.app_id == app_id)
            return model_to_dict(progress)
        except DoesNotExist:
            return None
    else:
        steps = {}
        for step, ProgressTable in progress_table_map.items():
            try:
                progress = ProgressTable.get(ProgressTable.app_id == app_id)
                steps[step] = model_to_dict(progress)
            except DoesNotExist:
                steps[step] = None

        return steps


def save_development_step(app_id, messages):
    app = get_app(app_id)
    hash_id = hash_data(messages)
    try:
        dev_step = DevelopmentSteps.create(app=app, hash_id=hash_id, messages=messages)
    except IntegrityError:
        print(f"A Development Step with hash_id {hash_id} already exists.")
        return None
    return dev_step


def get_development_step_by_hash_id(hash_id):
    try:
        dev_step = DevelopmentSteps.get(DevelopmentSteps.hash_id == hash_id)
    except DoesNotExist:
        print(f"No Development Step found with hash_id {hash_id}")
        return None
    return dev_step


def create_tables():
    with database:
        database.create_tables([
            User,
            App,
            ProjectDescription,
            UserStories,
            UserTasks,
            Architecture,
            DevelopmentPlanning,
            DevelopmentSteps,
            EnvironmentSetup,
            Development
        ])


def drop_tables():
    with database.atomic():
        for table in [User, App, ProjectDescription, UserStories, UserTasks, Architecture, DevelopmentPlanning, DevelopmentSteps, EnvironmentSetup, Development]:
            database.execute_sql(f'DROP TABLE IF EXISTS "{table._meta.table_name}" CASCADE')



if __name__ == "__main__":
    drop_tables()
    create_tables()
