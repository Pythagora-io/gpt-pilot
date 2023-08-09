from playhouse.shortcuts import model_to_dict
from peewee import *
from termcolor import colored
from functools import reduce
import operator

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
from database.models.file_snapshot import FileSnapshot
from database.models.command_runs import CommandRuns
from database.models.user_inputs import UserInputs


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


def save_development_step(app_id, prompt_path, prompt_data, llm_req_num, messages, response):
    app = get_app(app_id)
    hash_id = hash_data({
        'prompt_path': prompt_path,
        'prompt_data': {k: v for k, v in (prompt_data.items() if prompt_data is not None else {}) if k not in {"directory_tree"}},
        'llm_req_num': llm_req_num
    })
    try:
        inserted_id = (DevelopmentSteps
                       .insert(app=app, hash_id=hash_id, messages=messages, llm_response=response)
                       .on_conflict(conflict_target=[DevelopmentSteps.app, DevelopmentSteps.hash_id],
                                    preserve=[DevelopmentSteps.messages, DevelopmentSteps.llm_response],
                                    update={})
                       .execute())

        dev_step = DevelopmentSteps.get_by_id(inserted_id)
        print(colored(f"Saved DEV step => {dev_step.id}", "yellow"))
    except IntegrityError:
        print(f"A Development Step with hash_id {hash_id} already exists.")
        return None
    return dev_step


def get_db_model_from_hash_id(data_to_hash, model, app_id):
    hash_id = hash_data(data_to_hash)
    try:
        db_row = model.get((model.hash_id == hash_id) & (model.app == app_id))
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
    for field, value in data_fields.items():
        data_to_insert[field] = value

    try:
        inserted_id = (Model
                       .insert(**data_to_insert)
                       .on_conflict(conflict_target=[Model.app, Model.hash_id],
                                    preserve=[field for field in data_fields.keys()],
                                    update={})
                       .execute())

        record = Model.get_by_id(inserted_id)
        print(colored(f"{message} with id {record.id}", "yellow"))
    except IntegrityError:
        print(f"A record with hash_id {hash_id} already exists for {Model.__name__}.")
        return None
    return record


def save_command_run(project, command, cli_response):
    hash_data_args = {
        'command': command,
        'command_runs_count': project.command_runs_count,
    }
    data_fields = {
        'command': command,
        'cli_response': cli_response,
    }
    return hash_and_save_step(CommandRuns, project.args['app_id'], hash_data_args, data_fields, "Saved Command Run")


def get_command_run_from_hash_id(project, command):
    data_to_hash = {
        'command': command,
        'command_runs_count': project.command_runs_count
    }
    return get_db_model_from_hash_id(data_to_hash, CommandRuns, project.args['app_id'])

def save_user_input(project, query, user_input):
    hash_data_args = {
        'query': query,
        'user_inputs_count': project.user_inputs_count,
    }
    data_fields = {
        'query': query,
        'user_input': user_input,
    }
    return hash_and_save_step(UserInputs, project.args['app_id'], hash_data_args, data_fields, "Saved User Input")

def get_user_input_from_hash_id(project, query):
    data_to_hash = {
        'query': query,
        'user_inputs_count': project.user_inputs_count
    }
    return get_db_model_from_hash_id(data_to_hash, UserInputs, project.args['app_id'])


def get_development_step_from_hash_id(app_id, prompt_path, prompt_data, llm_req_num):
    if prompt_data is None:
        prompt_data_dict = {}
    else:
        prompt_data_dict = {k: v for k, v in prompt_data.items() if k not in {"directory_tree"}}

    hash_id = hash_data({
        'prompt_path': prompt_path,
        'prompt_data': prompt_data_dict,
        'llm_req_num': llm_req_num
    })

    try:
        dev_step = DevelopmentSteps.get((DevelopmentSteps.hash_id == hash_id) & (DevelopmentSteps.app == app_id))
    except DoesNotExist:
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
            Development,
            FileSnapshot,
            CommandRuns,
            UserInputs,
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
            ]:
            database.execute_sql(f'DROP TABLE IF EXISTS "{table._meta.table_name}" CASCADE')


if __name__ == "__main__":
    drop_tables()
    create_tables()
