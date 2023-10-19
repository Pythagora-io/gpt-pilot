# main.py
from __future__ import print_function, unicode_literals
import builtins
import os

import sys
import traceback
from dotenv import load_dotenv
load_dotenv()

from utils.style import color_red
from utils.custom_print import get_custom_print
from utils.custom_open import get_custom_open
from helpers.Project import Project
from utils.arguments import get_arguments
from utils.exit import exit_gpt_pilot
from logger.logger import logger
from database.database import database_exists, create_database, tables_exist, create_tables, get_created_apps_with_steps


def init():
    # Check if the "euclid" database exists, if not, create it
    if not database_exists():
        create_database()

    # Check if the tables exist, if not, create them
    if not tables_exist():
        create_tables()

    arguments = get_arguments()

    logger.info('Starting with args: %s', arguments)

    return arguments


if __name__ == "__main__":
    ask_feedback = True
    try:
        # sys.argv.append('--ux-test=' + 'continue_development')
        args = init()
        builtins.print, ipc_client_instance = get_custom_print(args)
        # Override the built-in 'open' with our version
        builtins.open = get_custom_open

        if '--api-key' in args:
            os.environ["OPENAI_API_KEY"] = args['--api-key']
        if '--get-created-apps-with-steps' in args:
            if ipc_client_instance is not None:
                print({ 'db_data': get_created_apps_with_steps() }, type='info')
            else:
                print('----------------------------------------------------------------------------------------')
                print('app_id                                step                 dev_step  name')
                print('----------------------------------------------------------------------------------------')
                print('\n'.join(f"{app['id']}: {app['status']:20}      "
                                f"{'' if len(app['development_steps']) == 0 else app['development_steps'][-1]['id']:3}"
                                f"  {app['name']}" for app in get_created_apps_with_steps()))
        elif '--ux-test' in args:
            from test.ux_tests import run_test
            run_test(args['--ux-test'], args)
        else:
            # TODO get checkpoint from database and fill the project with it
            project = Project(args, ipc_client_instance=ipc_client_instance)
            project.start()
            project.finish()
    except Exception:
        print(color_red('---------- GPT PILOT EXITING WITH ERROR ----------'))
        traceback.print_exc()
        print(color_red('--------------------------------------------------'))
        ask_feedback = False
    finally:
        exit_gpt_pilot(ask_feedback)
        sys.exit(0)
