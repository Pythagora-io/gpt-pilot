from playhouse.shortcuts import model_to_dict
from peewee import *
from termcolor import colored
from functools import reduce
import operator
import psycopg2
from const.common import PROMPT_DATA_TO_IGNORE
from logger.logger import logger
from psycopg2.extensions import quote_ident

from utils.utils import hash_data
from database.config import DB_NAME, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DATABASE_TYPE
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
from database.models.user_inputs import UserInputs
from database.models.files import File


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


def save_app(args):
    try:
        app = App.get(App.id == args['app_id'])
        for key, value in args.items():
            if key != 'app_id' and value is not None:
                setattr(app, key, value)
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
            name=args.get('name')
        )

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


def get_db_model_from_hash_id(model, app_id, previous_step):
    try:
        db_row = model.get((model.app == app_id) & (model.previous_step == previous_step))
    except DoesNotExist:
        return None
    return db_row


def hash_and_save_step(Model, app_id, hash_data_args, data_fields, message):
    app = get_app(app_id)
    hash_id = hash_data(hash_data_args)

    data_to_insert = {
        'app': app,
        'hash_id': hash_id
    }

    fields_to_preserve = [getattr(Model, field) for field in list(data_to_insert.keys())]

    for field, value in data_fields.items():
        data_to_insert[field] = value

    try:
        inserted_id = (Model
                       .insert(**data_to_insert)
                       .on_conflict(conflict_target=[Model.app, Model.hash_id],
                                    preserve=fields_to_preserve,
                                    update=data_fields)
                       .execute())

        record = Model.get_by_id(inserted_id)
        logger.debug(colored(f"{message} with id {record.id}", "yellow"))
    except IntegrityError:
        print(f"A record with hash_id {hash_id} already exists for {Model.__name__}.")
        return None
    return record


def save_development_step(project, prompt_path, prompt_data, messages, llm_response):
    hash_data_args = {
        'prompt_path': prompt_path,
        'prompt_data': {} if prompt_data is None else {k: v for k, v in prompt_data.items() if
                                                       k not in PROMPT_DATA_TO_IGNORE},
        'llm_req_num': project.llm_req_num
    }

    data_fields = {
        'messages': messages,
        'llm_response': llm_response,
        'previous_step': project.checkpoints['last_development_step'],
    }

    development_step = hash_and_save_step(DevelopmentSteps, project.args['app_id'], hash_data_args, data_fields, "Saved Development Step")
    project.checkpoints['last_development_step'] = development_step


    project.save_files_snapshot(development_step.id)


    return development_step


def get_development_step_from_hash_id(project, prompt_path, prompt_data, llm_req_num):
    data_to_hash = {
        'prompt_path': prompt_path,
        'prompt_data': {} if prompt_data is None else {k: v for k, v in prompt_data.items() if
                                                       k not in PROMPT_DATA_TO_IGNORE},
        'llm_req_num': llm_req_num
    }
    development_step = get_db_model_from_hash_id(DevelopmentSteps, project.args['app_id'],
                                                 project.checkpoints['last_development_step'])
    return development_step


def save_command_run(project, command, cli_response):
    hash_data_args = {
        'command': command,
        'command_runs_count': project.command_runs_count,
    }
    data_fields = {
        'command': command,
        'cli_response': cli_response,
        'previous_step': project.checkpoints['last_command_run'],
    }
    command_run = hash_and_save_step(CommandRuns, project.args['app_id'], hash_data_args, data_fields,
                                     "Saved Command Run")
    project.checkpoints['last_command_run'] = command_run
    return command_run


def get_command_run_from_hash_id(project, command):
    data_to_hash = {
        'command': command,
        'command_runs_count': project.command_runs_count
    }
    command_run = get_db_model_from_hash_id(CommandRuns, project.args['app_id'],
                                            project.checkpoints['last_command_run'])
    return command_run


def save_user_input(project, query, user_input):
    hash_data_args = {
        'query': query,
        'user_inputs_count': project.user_inputs_count,
    }
    data_fields = {
        'query': query,
        'user_input': user_input,
        'previous_step': project.checkpoints['last_user_input'],
    }
    user_input = hash_and_save_step(UserInputs, project.args['app_id'], hash_data_args, data_fields, "Saved User Input")
    project.checkpoints['last_user_input'] = user_input
    return user_input


def get_user_input_from_hash_id(project, query):
    data_to_hash = {
        'query': query,
        'user_inputs_count': project.user_inputs_count
    }
    user_input = get_db_model_from_hash_id(UserInputs, project.args['app_id'], project.checkpoints['last_user_input'])
    return user_input


def delete_all_subsequent_steps(project):
    delete_subsequent_steps(DevelopmentSteps, project.checkpoints['last_development_step'])
    delete_subsequent_steps(CommandRuns, project.checkpoints['last_command_run'])
    delete_subsequent_steps(UserInputs, project.checkpoints['last_user_input'])


def delete_subsequent_steps(model, step):
    if step is None:
        return
    logger.info(colored(f"Deleting subsequent {model.__name__} steps after {step.id}", "red"))
    subsequent_steps = model.select().where(model.previous_step == step.id)
    for subsequent_step in subsequent_steps:
        if subsequent_step:
            delete_subsequent_steps(model, subsequent_step)
            subsequent_step.delete_instance()


def get_all_connected_steps(step, previous_step_field_name):
    """Recursively get all steps connected to the given step."""
    connected_steps = [step]
    prev_step = getattr(step, previous_step_field_name)
    while prev_step is not None:
        connected_steps.append(prev_step)
        prev_step = getattr(prev_step, previous_step_field_name)
    return connected_steps


def delete_all_app_development_data(app):
    models = [DevelopmentSteps, CommandRuns, UserInputs, File, FileSnapshot]
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
        print(colored(f"Deleting unconnected {step.__class__.__name__} step {unconnected_step.id}", "red"))
        unconnected_step.delete_instance()


def save_file_description(project, path, name, description):
    (File.insert(app=project.app, path=path, name=name, description=description)
     .on_conflict(
        conflict_target=[File.app, File.name, File.path],
        preserve=[],
        update={'description': description})
     .execute())


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
            Development,
            FileSnapshot,
            CommandRuns,
            UserInputs,
            File,
        ])


def drop_tables():
    with database.atomic():
        for table in [
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
            UserInputs,
            File,
        ]:
            if DATABASE_TYPE == "postgresql":
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
    tables = [User, App, ProjectDescription, UserStories, UserTasks, Architecture, DevelopmentPlanning,
              DevelopmentSteps, EnvironmentSetup, Development, FileSnapshot, CommandRuns, UserInputs, File]

    if DATABASE_TYPE == "postgres":
        for table in tables:
            try:
                database.get_tables().index(table._meta.table_name)
            except ValueError:
                return False
    else:
        pass
    return True


if __name__ == "__main__":
    drop_tables()
    create_tables()
