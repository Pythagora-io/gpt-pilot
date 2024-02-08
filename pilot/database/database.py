from playhouse.shortcuts import model_to_dict
from utils.style import color_yellow, color_red
from peewee import DoesNotExist, IntegrityError
from functools import reduce
import operator
from database.config import DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DATABASE_TYPE
if DATABASE_TYPE == "postgres":
    import psycopg2
    from psycopg2.extensions import quote_ident

import os
from const.common import PROMPT_DATA_TO_IGNORE, STEPS
from logger.logger import logger
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
from database.models.file_snapshot import FileSnapshot
from database.models.command_runs import CommandRuns
from database.models.user_apps import UserApps
from database.models.user_inputs import UserInputs
from database.models.files import File
from database.models.feature import Feature

TABLES = [
            User,
            App,
            ProjectDescription,
            UserStories,
            UserTasks,
            Architecture,
            DevelopmentPlanning,
            DevelopmentSteps,
            EnvironmentSetup,
            Development,
            FileSnapshot,
            CommandRuns,
            UserApps,
            UserInputs,
            File,
            Feature,
        ]


def get_created_apps():
    return [model_to_dict(app) for app in App.select().where((App.name.is_null(False)) & (App.status.is_null(False)))]


def get_created_apps_with_steps():
    apps = get_created_apps()
    for app in apps:
        app['id'] = str(app['id'])
        app['steps'] = [step for step in STEPS[:STEPS.index(app['status']) + 1]] if app['status'] is not None else []
        app['development_steps'] = get_all_app_development_steps(app['id'])
        # TODO this is a quick way to remove the unnecessary fields from the response
        app['development_steps'] = [{k: v for k, v in dev_step.items() if k in {'id', 'created_at'}} for dev_step in
                                    app['development_steps']]
    return apps


def get_all_app_development_steps(app_id, last_step=None):
    query = DevelopmentSteps.select().where(DevelopmentSteps.app == app_id)

    if last_step is not None:
        query = query.where(DevelopmentSteps.id <= last_step)

    return [model_to_dict(dev_step) for dev_step in query]


def save_user(user_id, email, password):
    try:
        user = User.get(User.id == user_id)
        return user
    except DoesNotExist:
        try:
            existing_user = User.get(User.email == email)
            return existing_user
        except DoesNotExist:
            return User.create(id=user_id, email=email, password=password)


def update_app_status(app_id, new_status):
    try:
        app = App.get(App.id == app_id)
        app.status = new_status
        app.save()
        return True
    except DoesNotExist:
        return False


def get_user(user_id=None, email=None):
    if not user_id and not email:
        raise ValueError("Either user_id or email must be provided")

    query = []
    if user_id:
        query.append(User.id == user_id)
    if email:
        query.append(User.email == email)

    try:
        user = User.get(reduce(operator.or_, query))
        return user
    except DoesNotExist:
        raise ValueError("No user found with provided id or email")


def save_app(project):
    args = project.args
    app_status = getattr(project, "current_step", None)

    try:
        app = project.app
        if app is None:
            app = App.get(App.id == args['app_id'])
        for key, value in args.items():
            if key != 'app_id' and value is not None:
                setattr(app, key, value)

        app.status = app_status
        app.save()
    except DoesNotExist:
        if args.get('user_id') is not None:
            try:
                user = get_user(user_id=args['user_id'])
            except ValueError:
                user = save_user(args['user_id'], args['email'], args['password'])
                args['user_id'] = user.id
                args['email'] = user.email
        else:
            user = None

        app = App.create(
            id=args['app_id'],
            user=user,
            app_type=args.get('app_type'),
            name=args.get('name'),
            status=app_status
        )

    return app


def save_user_app(user_id, app_id, workspace):
    try:
        user_app = UserApps.get((UserApps.user == user_id) & (UserApps.app == app_id))
        user_app.workspace = workspace
        user_app.save()
    except DoesNotExist:
        user_app = UserApps.create(user=user_id, app=app_id, workspace=workspace)

    return user_app


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

    update_app_status(app_id, step)
    return progress


def get_app(app_id, error_if_not_found=True):
    try:
        app = App.get(App.id == app_id)
        return app
    except DoesNotExist:
        if error_if_not_found:
            raise ValueError(f"No app with id: {app_id}; use python main.py --get-created-apps-with-steps to see created apps")
        return None


def get_app_by_user_workspace(user_id, workspace):
    try:
        user_app = UserApps.get((UserApps.user == user_id) & (UserApps.workspace == workspace))
        return user_app.app
    except DoesNotExist:
        return None


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


def get_db_model_from_hash_id(model, app_id, previous_step, high_level_step):
    try:
        db_row = model.get(
            (model.app == app_id) & (model.previous_step == previous_step) & (model.high_level_step == high_level_step))
    except DoesNotExist:
        return None
    return db_row


def hash_and_save_step(Model, app_id, unique_data_fields, data_fields, message):
    # app = get_app(app_id)

    # fields_to_preserve = [getattr(Model, field) for field in list(unique_data_fields.keys())]

    for field, value in data_fields.items():
        unique_data_fields[field] = value

    try:
        # existing_record = Model.get_or_none(
        #     (Model.app == app) & (Model.previous_step == unique_data_fields['previous_step']) & (
        #                 Model.high_level_step == unique_data_fields['high_level_step']))
        inserted_id = (Model
                       .insert(**unique_data_fields)
                       .execute())

        record = Model.get_by_id(inserted_id)
        logger.debug(color_yellow(f"{message} with id {record.id}"))
    except IntegrityError:
        logger.warn(f"A record with data {unique_data_fields} already exists for {Model.__name__}.")
        return None
    return record


def save_development_step(project, prompt_path, prompt_data, messages, llm_response, exception=None):
    data_fields = {
        'messages': messages,
        'llm_response': llm_response,
        'prompt_path': prompt_path,
        'prompt_data': {} if prompt_data is None else {k: v for k, v in prompt_data.items() if
                                                       k not in PROMPT_DATA_TO_IGNORE and not callable(v)},
        'llm_req_num': project.llm_req_num,
        'token_limit_exception_raised': exception
    }

    unique_data = {
        'app': project.args['app_id'],
        'previous_step': project.checkpoints['last_development_step']['id'] if project.checkpoints['last_development_step'] else None,
        'high_level_step': project.current_step,
    }

    development_step = hash_and_save_step(DevelopmentSteps, project.args['app_id'], unique_data, data_fields,
                                          "Saved Development Step")
    project.checkpoints['last_development_step'] = model_to_dict(development_step)

    project.save_files_snapshot(development_step.id)


def save_command_run(project, command, cli_response, done_or_error_response, exit_code):
    if project.current_step != 'coding':
        return

    unique_data = {
        'app': project.args['app_id'],
        'previous_step': project.checkpoints['last_command_run'],
        'high_level_step': project.current_step,
    }

    data_fields = {
        'command': command,
        'cli_response': cli_response,
        'done_or_error_response': done_or_error_response,
        'exit_code': exit_code,
    }

    command_run = hash_and_save_step(CommandRuns, project.args['app_id'], unique_data, data_fields, "Saved Command Run")
    project.checkpoints['last_command_run'] = command_run
    return command_run


def save_user_input(project, query, user_input, hint):
    if project.current_step != 'coding':
        return

    unique_data = {
        'app': project.args['app_id'],
        'previous_step': project.checkpoints['last_user_input'],
        'high_level_step': project.current_step,
    }
    data_fields = {
        'query': query,
        'user_input': user_input,
        'hint': hint,
    }
    user_input = hash_and_save_step(UserInputs, project.args['app_id'], unique_data, data_fields, "Saved User Input")
    project.checkpoints['last_user_input'] = user_input
    return user_input


def delete_all_subsequent_steps(project):
    app = get_app(project.args['app_id'])
    delete_subsequent_steps(DevelopmentSteps, app, project.checkpoints['last_development_step'])
    # after implementation of backwards compatibility, we don't need to delete subsequent steps for CommandRuns and UserInputs
    # delete_subsequent_steps(CommandRuns, app, project.checkpoints['last_command_run'])
    # delete_subsequent_steps(UserInputs, app, project.checkpoints['last_user_input'])


def delete_subsequent_steps(Model, app, step):
    if isinstance(step, dict):
        step_id = step.get('id')
    elif hasattr(step, 'id'):
        step_id = step.id
    else:
        step_id = None
    logger.info(color_red(f"Deleting subsequent {Model.__name__} steps after {step_id}"))

    subsequent_steps = Model.select().where(
        (Model.app == app) & (Model.previous_step == step_id))

    for subsequent_step in subsequent_steps:
        if subsequent_step:
            delete_subsequent_steps(Model, app, subsequent_step)
            subsequent_step.delete_instance()
            if Model == DevelopmentSteps:
                FileSnapshot.delete().where(FileSnapshot.development_step == subsequent_step).execute()
                Feature.delete().where(Feature.previous_step == subsequent_step).execute()


def get_all_connected_steps(step, previous_step_field_name):
    """Recursively get all steps connected to the given step."""
    connected_steps = [step]
    prev_step = getattr(step, previous_step_field_name)
    while prev_step is not None:
        connected_steps.append(prev_step)
        prev_step = getattr(prev_step, previous_step_field_name)
    return connected_steps


def delete_all_app_development_data(app):
    models = [DevelopmentSteps, CommandRuns, UserInputs, UserApps, File, FileSnapshot]
    for model in models:
        model.delete().where(model.app == app).execute()


def delete_unconnected_steps_from(step, previous_step_field_name):
    if step is None:
        return
    connected_steps = get_all_connected_steps(step, previous_step_field_name)
    connected_step_ids = [s.id for s in connected_steps]

    unconnected_steps = DevelopmentSteps.select().where(
        (DevelopmentSteps.app == step.app) &
        (DevelopmentSteps.id.not_in(connected_step_ids))
    ).order_by(DevelopmentSteps.id.desc())

    for unconnected_step in unconnected_steps:
        print(color_red(f"Deleting unconnected {step.__class__.__name__} step {unconnected_step.id}"))
        unconnected_step.delete_instance()


def save_file_description(project, path, name, description):
    (File.insert(app=project.app, path=path, name=name, description=description)
     .on_conflict(
        conflict_target=[File.app, File.name, File.path],
        preserve=[],
        update={'description': description})
     .execute())


def save_feature(app_id, summary, messages, previous_step):
    try:
        app = get_app(app_id)
        feature = Feature.create(app=app, summary=summary, messages=messages, previous_step=previous_step)
        return feature
    except DoesNotExist:
        raise ValueError(f"No app with id: {app_id}")


def get_features_by_app_id(app_id):
    try:
        app = get_app(app_id)
        features = DevelopmentSteps.select().where(
            (DevelopmentSteps.app_id == app) &
            (DevelopmentSteps.prompt_path.contains("feature_plan"))
        ).order_by(DevelopmentSteps.created_at)
        features_dict = [model_to_dict(feature) for feature in features]

        # return only 'summary' because we store all prompt_data to DB
        return [{'summary': feature['prompt_data']['feature_description'], 'id': feature['id']} for feature in features_dict]
    except DoesNotExist:
        raise ValueError(f"No app with id: {app_id}")


def create_tables():
    with database:
        database.create_tables(TABLES)


def drop_tables():
    with database.atomic():
        for table in TABLES:
            if DATABASE_TYPE == "postgres":
                sql = f'DROP TABLE IF EXISTS "{table._meta.table_name}" CASCADE'
            elif DATABASE_TYPE == "sqlite":
                sql = f'DROP TABLE IF EXISTS "{table._meta.table_name}"'
            else:
                raise ValueError(f"Unsupported DATABASE_TYPE: {DATABASE_TYPE}")

            database.execute_sql(sql)


def database_exists():
    try:
        database.connect()
        database.close()
        return True
    except Exception:
        return False


def create_database():
    if DATABASE_TYPE == "postgres":
        # Connect to the default 'postgres' database to create a new database
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Safely quote the database name
        safe_db_name = quote_ident(DB_NAME, conn)

        # Use the safely quoted database name in the SQL query
        cursor.execute(f"CREATE DATABASE {safe_db_name}")

        cursor.close()
        conn.close()
    else:
        pass


def tables_exist():
    for table in TABLES:
        try:
            database.get_tables().index(table._meta.table_name)
        except ValueError:
            return False
    return True


if __name__ == "__main__":
    drop_tables()
    create_tables()
