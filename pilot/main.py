# main.py
import builtins
import json
import os

import sys
import traceback

try:
    from dotenv import load_dotenv
except ImportError:
    raise RuntimeError('Python environment for GPT Pilot is not completely set up: required package "python-dotenv" is missing.') from None

load_dotenv()

from utils.style import color_red
from utils.custom_print import get_custom_print
from helpers.Project import Project
from utils.arguments import get_arguments
from utils.exit import exit_gpt_pilot
from logger.logger import logger
from database.database import database_exists, create_database, tables_exist, create_tables, get_created_apps_with_steps

from utils.settings import settings, loader, get_version
from utils.telemetry import telemetry
from helpers.exceptions import ApiError, TokenLimitError, GracefulExit

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
    project = None
    run_exit_fn = True

    args = init()

    try:
        # sys.argv.append('--ux-test=' + 'continue_development')

        builtins.print, ipc_client_instance = get_custom_print(args)

        if '--api-key' in args:
            os.environ["OPENAI_API_KEY"] = args['--api-key']
        if '--api-endpoint' in args:
            os.environ["OPENAI_ENDPOINT"] = args['--api-endpoint']

        if '--get-created-apps-with-steps' in args:
            run_exit_fn = False

            if ipc_client_instance is not None:
                print({ 'db_data': get_created_apps_with_steps() }, type='info')
            else:
                print('----------------------------------------------------------------------------------------')
                print('app_id                                step                 dev_step  name')
                print('----------------------------------------------------------------------------------------')
                print('\n'.join(f"{app['id']}: {app['status']:20}      "
                                f"{'' if len(app['development_steps']) == 0 else app['development_steps'][-1]['id']:3}"
                                f"  {app['name']}" for app in get_created_apps_with_steps()))

        elif '--version' in args:
            print(get_version())
            run_exit_fn = False

        elif '--ux-test' in args:
            from test.ux_tests import run_test
            run_test(args['--ux-test'], args)
            run_exit_fn = False
        else:
            if settings.telemetry is None:
                telemetry.setup()
                loader.save("telemetry")

            if args.get("app_id"):
                telemetry.set("is_continuation", True)

            if "email" in args:
                telemetry.set("user_contact", args["email"])

            if "extension_version" in args:
                telemetry.set("extension_version", args["extension_version"])

            # TODO get checkpoint from database and fill the project with it
            project = Project(args, ipc_client_instance=ipc_client_instance)
            if project.check_ipc():
                telemetry.set("is_extension", True)

            started = project.start()
            if started:
                project.finish()
                telemetry.set("end_result", "success:exit")
            else:
                run_exit_fn = False
                telemetry.set("end_result", "failure:api-error")
                print('Exit', type='exit')

    except (ApiError, TokenLimitError) as err:
        telemetry.record_crash(err, end_result="failure:api-error")
        telemetry.send()
        run_exit_fn = False
        print('Exit', type='exit')

    except KeyboardInterrupt:
        telemetry.set("end_result", "interrupt")
        if project is not None and project.check_ipc():
            telemetry.send()
            run_exit_fn = False

    except GracefulExit:
        # can't call project.finish_loading() here because project can be None
        run_exit_fn = False
        print('', type='loadingFinished')
        print('Exit', type='exit')

    except Exception as err:
        print(color_red('---------- GPT PILOT EXITING WITH ERROR ----------'))
        traceback.print_exc()
        print(color_red('--------------------------------------------------'))
        ask_feedback = False
        telemetry.record_crash(err)

    finally:
        if project is not None:
            project.current_task.exit()
            project.finish_loading(do_cleanup=False)
        if run_exit_fn:
            exit_gpt_pilot(project, ask_feedback)
