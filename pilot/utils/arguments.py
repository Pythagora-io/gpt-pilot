import hashlib
import os
import re
import sys
import uuid
from getpass import getuser
from database.database import get_app, get_app_by_user_workspace
from utils.style import color_green_bold, color_red, style_config
from utils.utils import should_execute_step
from const.common import STEPS


def get_arguments():
    # The first element in sys.argv is the name of the script itself.
    # Any additional elements are the arguments passed from the command line.
    args = sys.argv[1:]

    # Create an empty dictionary to store the key-value pairs.
    arguments = {
        'continuing_project': False
    }

    # Loop through the arguments and parse them as key-value pairs.
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            arguments[key] = value
        else:
            arguments[arg] = True

    theme_mapping = {'light': style_config.theme.LIGHT, 'dark': style_config.theme.DARK}
    theme_value = arguments.get('theme', 'dark')
    style_config.set_theme(theme=theme_mapping.get(theme_value, style_config.theme.DARK))

    if 'user_id' not in arguments:
        arguments['user_id'] = username_to_uuid(getuser())

    app = None
    if 'workspace' in arguments:
        arguments['workspace'] = os.path.abspath(arguments['workspace'])
        app = get_app_by_user_workspace(arguments['user_id'], arguments['workspace'])
        if app is not None:
            arguments['app_id'] = str(app.id)
            arguments['continuing_project'] = True
    else:
        arguments['workspace'] = None

    if 'app_id' in arguments:
        if app is None:
            try:
                app = get_app(arguments['app_id'])
            except ValueError as err:
                print(color_red(f"Error: {err}"))
                sys.exit(-1)

        arguments['app_type'] = app.app_type
        arguments['name'] = app.name
        arguments['status'] = app.status
        arguments['continuing_project'] = True
        if 'step' not in arguments or ('step' in arguments and not should_execute_step(arguments['step'], app.status)):
            arguments['step'] = 'finished' if app.status == 'finished' else STEPS[STEPS.index(app.status) + 1]

        print(color_green_bold('\n------------------ LOADING PROJECT ----------------------'))
        print(color_green_bold(f'{app.name} (app_id={arguments["app_id"]})'))
        print(color_green_bold('--------------------------------------------------------------\n'))

    elif '--get-created-apps-with-steps' not in args and '--version' not in args:
        arguments['app_id'] = str(uuid.uuid4())
        print(color_green_bold('\n------------------ STARTING NEW PROJECT ----------------------'))
        print("If you wish to continue with this project in future run:")
        print(color_green_bold(f'python {sys.argv[0]} app_id={arguments["app_id"]}'))
        print(color_green_bold('--------------------------------------------------------------\n'))

    if 'email' not in arguments:
        arguments['email'] = get_email()

    if 'password' not in arguments:
        arguments['password'] = 'password'

    if 'step' not in arguments:
        arguments['step'] = None

    return arguments


def get_email():
    # Attempt to get email from .gitconfig
    gitconfig_path = os.path.expanduser('~/.gitconfig')

    if os.path.exists(gitconfig_path):
        with open(gitconfig_path, 'r', encoding="utf-8") as file:
            content = file.read()

            # Use regex to search for email address
            email_match = re.search(r'email\s*=\s*([\w\.-]+@[\w\.-]+)', content)

            if email_match:
                return email_match.group(1)

    # If not found, return a UUID
    # todo change email so its not uuid4 but make sure to fix storing of development steps where
    #  1 user can have multiple apps. In that case each app should have its own development steps
    return str(uuid.uuid4())


# TODO can we make BaseModel.id a CharField with default=uuid4?
def username_to_uuid(username):
    """
    Creates a consistent UUID from a username
    :param username:
    :return:
    """
    sha1 = hashlib.sha1(username.encode()).hexdigest()
    uuid_str = "{}-{}-{}-{}-{}".format(sha1[:8], sha1[8:12], sha1[12:16], sha1[16:20], sha1[20:32])
    return str(uuid.UUID(uuid_str))
