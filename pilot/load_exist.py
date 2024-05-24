# ------------------------------------------------------------------------------
# usage:
#  cd to gpt-pilot VS Code Extension xxx/gpt-pilot
#  copy /my_project to xxx/gpt-pilot/workspace
#  cd xxx/gpt-pilot/pilot
#  python ./load_exist.py name=my_project
#  open VS Code Extension
#  Click 'Load App' button, and select 'my_project', then click 'Load' button,choice 'Yes' twice
#  It will directly goto the develpment step finsh status,and ask you to input the next feature,
#  then you can input your new feature requirements to continue the development.
# ------------------------------------------------------------------------------
import builtins
import json
import os
import platform
import sys
import traceback


try:
    from dotenv import load_dotenv
except ImportError:
    gpt_pilot_root = os.path.dirname(os.path.dirname(__file__))
    venv_path = os.path.join(gpt_pilot_root, 'pilot-env')
    requirements_path = os.path.join(gpt_pilot_root, 'requirements.txt')
    if sys.prefix == sys.base_prefix:
        venv_python_path = os.path.join(venv_path, 'scripts' if sys.platform == 'win32' else 'bin', 'python')
        print('Python environment for GPT Pilot is not set up.')
        print(f'Please create Python virtual environment: {sys.executable} -m venv {venv_path}')
        print(f'Then install the required dependencies with: {venv_python_path} -m pip install -r {requirements_path}')
    else:
        print('Python environment for GPT Pilot is not completely set up.')
        print(f'Please run `{sys.executable} -m pip install -r {requirements_path}` to finish Python setup, and rerun GPT Pilot.')
    sys.exit(-1)

load_dotenv(override=True)

from const.function_calls import GET_DOCUMENTATION_FILE, ARCHITECTURE, DEVELOPMENT_PLAN
from helpers.Project import Project
from helpers.AgentConvo import AgentConvo
from helpers.agents.TechnicalWriter import TechnicalWriter
from helpers.exceptions import ApiError, TokenLimitError, GracefulExit
from helpers.files import get_directory_contents
from helpers.agents.ProductOwner import PROJECT_DESCRIPTION_STEP
from helpers.agents import Architect, ARCHITECTURE_STEP, ENVIRONMENT_SETUP_STEP, TechLead
from helpers.agents.TechLead import DEVELOPMENT_PLANNING_STEP

from templates import PROJECT_TEMPLATES
from utils.utils import generate_app_data
from utils.style import color_red
from utils.custom_print import get_custom_print
from utils.arguments import get_arguments
from utils.exit import exit_gpt_pilot
from utils.settings import settings, loader, get_version
from logger.logger import logger
from database.models.app import App
from peewee import DoesNotExist
from database.database import (
    database_exists,
    create_database,
    tables_exist,
    create_tables,
    save_app,
    get_created_apps,
    save_development_step, save_progress, update_app_status,
)


def init():
    # Check if the database exists, if not, create it
    if not database_exists():
        create_database()

    # Check if the tables exist, if not, create them
    if not tables_exist():
        create_tables()

    arguments = get_arguments()

    logger.info('Starting with args: %s', arguments)

    return arguments


def exit_if_app_not_in_workspace():
    if not os.path.exists(app_root_path):
        print(f'App {app_name} does not exist in the workspace directory.')
        sys.exit(-1)


def planning_architecture():
    global convo, llm_response
    print("Planning project architecture...\n")
    project.architect = Architect(project)
    convo = AgentConvo(project.architect)
    llm_response = convo.send_message('architecture/technologies.prompt',
                                      {'name': project.args['name'],
                                       'app_summary': project.project_description,
                                       'user_stories': project.user_stories,
                                       'user_tasks': project.user_tasks,
                                       "os": platform.system(),
                                       'app_type': project.args['app_type'],
                                       "templates": PROJECT_TEMPLATES,
                                       },
                                      ARCHITECTURE
                                      )
    project.architecture = llm_response["architecture"]
    project.system_dependencies = llm_response["system_dependencies"]
    project.package_dependencies = llm_response["package_dependencies"]
    project.project_template = llm_response["template"]

    save_progress(app.id, ARCHITECTURE_STEP, {
        "messages": convo.messages,
        "architecture": llm_response,
        "app_data": app_data
    })


def load_codebase():
    global messages, llm_response
    prompt_path = "development/task/breakdown.prompt"
    prompt_data = {"app_summary": "", "tasks": [{"description": "Implement Nothing", "finished": False}], "current_task": "Nothing", "files": [], "file_summaries": {}, "all_feedbacks": [], "modified_files": [], "files_at_start_of_task": [], "previous_features": None, "current_feature": None}
    messages = '''[{"role": "system", "content": ""},{"role": "user", "content": ""}]'''
    llm_response = {'text': 'DONE'}
    save_development_step(project, prompt_path, prompt_data, messages, llm_response, exception=None)


def summary_codebase():
    global project
    print('Creating project description')
    project.technical_writer = TechnicalWriter(project)
    convo = AgentConvo(project.technical_writer)
    llm_response = convo.send_message('documentation/summary_codebase.prompt', {
        "name": project.args['name'],
        "app_type": project.app_type,
        "app_summary": project.project_description,
        "user_stories": project.user_stories,
        "user_tasks": project.user_tasks,
        "directory_tree": project.get_directory_tree(True),
        "files": project.get_all_coded_files(),
        "previous_features": project.previous_features,
        "current_feature": project.current_feature,
    }, GET_DOCUMENTATION_FILE)
    app_summary = llm_response.get('content')
    project.project_description = app_summary
    save_progress(app.id, PROJECT_DESCRIPTION_STEP, {
        "prompt": app_summary,
        "messages": [],
        "summary": app_summary,
        "app_data": app_data
    })


def setup_environment():
    print("Setting up the environment...\n")
    save_progress(app.id, ENVIRONMENT_SETUP_STEP, {
        "os_specific_technologies": project.system_dependencies,
        "newly_installed_technologies": [],
        "app_data": app_data
    })


def planning_development():
    global llm_response, project
    print('Plan for development is created.\n')
    project.development_plan = [{"description": "Load exist codebase"}]
    save_progress(app.id, DEVELOPMENT_PLANNING_STEP, {
        "development_plan": project.development_plan, "app_data": app_data
    })


if __name__ == "__main__":
    '''
    This script is used to load the existing app from the workspace directory.
    It will check if the app exists in the database, if not, it will create it by summaries codes.
    '''
    ask_feedback = True
    project = None
    run_exit_fn = True
    gpt_pilot_root = os.path.dirname(os.path.dirname(__file__))
    workspace_path = os.path.join(gpt_pilot_root, 'workspace')
    args = init()
    try:
        builtins.print, ipc_client_instance = get_custom_print(args)
        run_exit_fn = False
        app_name = args.get('name')
        app_root_path = os.path.join(workspace_path, app_name)
        print('----------------------------------------------------------------------------------------')
        print(f'Loading App { app_name }，{ app_root_path }')
        print('----------------------------------------------------------------------------------------')

        exit_if_app_not_in_workspace()

        if 'app_type' not in args:
            args['app_type'] = 'App'


        project = Project(args)
        project.set_root_path(app_root_path)
        try:
            app = App.get(App.name == app_name)
            if app.status:
                print(f'App {app_name} already exist in database.')
                sys.exit(-1)
        except DoesNotExist:
            project.app = None
            if 'new_app_id' in args:
                project.args['app_id'] = args['new_app_id']

            app = save_app(project)
            print(f'App {app_name} saved in database.')

        project.app = app
        project.args['app_id'] = str(app.id)
        project.app_type = args['app_type']
        project.current_step = 'loading'
        project.skip_steps = True

        load_codebase()

        project.files = project.get_all_coded_files()
        app_data = generate_app_data(project.args)
        summary_codebase()
        planning_architecture()
        setup_environment()
        planning_development()
        project.technical_writer.create_readme()

        print('Load exist App done.')

    except (ApiError, TokenLimitError) as err:

        run_exit_fn = False
        if isinstance(err, TokenLimitError):
            print(
                "We sent too large request to the LLM, resulting in an error. "
                "This is usually caused by including framework files in an LLM request. "
                "Here's how you can get GPT Pilot to ignore those extra files: "
                "https://bit.ly/faq-token-limit-error"
            )
        print('Exit')

    except KeyboardInterrupt:
        if project is not None and project.check_ipc():
            run_exit_fn = False

    except GracefulExit:
        # can't call project.finish_loading() here because project can be None
        run_exit_fn = False
        print('Exit')

    except Exception as err:
        print(color_red('---------- GPT PILOT EXITING WITH ERROR ----------'))
        print(err)
        traceback.print_exc()
        print(color_red('--------------------------------------------------'))
        ask_feedback = False

    finally:
        if project is not None:
            if project.check_ipc():
                ask_feedback = False
            project.current_task.exit()
            project.finish_loading(do_cleanup=False)
        if run_exit_fn:
            exit_gpt_pilot(project, ask_feedback)
