import argparse
import hashlib
import os
import re
import sys
import uuid
from getpass import getuser
from database.database import get_app, get_app_by_user_workspace
from utils.style import color_green_bold, style_config
from utils.utils import should_execute_step
from const.common import STEPS

def get_arguments():

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser()

    # Add command-line arguments with their types and default values
    parser.add_argument('--user_id', type=str, default=username_to_uuid(getuser()))
    parser.add_argument('--workspace', type=str, default=None)
    parser.add_argument('--app_id', type=str, default=str(uuid.uuid4()))
    parser.add_argument('--email', type=str, default=get_email())
    parser.add_argument('--password', type=str, default='password')
    parser.add_argument('--step', type=str, default=None)

    # Parse the command-line arguments
    arguments = parser.parse_args()

    # Initialize app as None
    app = None

    # If workspace is provided, get the corresponding app
    if arguments.workspace:
        app = get_app_by_user_workspace(arguments.user_id, arguments.workspace)
        if app is not None:
            arguments.app_id = app.id
    else:
        arguments.workspace = None

    # If app_id is provided, get the app details and print them
    if arguments.app_id:
        try:
            if app is None:
                app = get_app(arguments.app_id)

            arguments.app_type = app.app_type
            arguments.name = app.name
            arguments.step = app.status
            # Add any other fields from the App model you wish to include

            print(green_bold('\n------------------ LOADING PROJECT ----------------------'))
            print(green_bold(f'{app.name} (app_id={arguments.app_id})'))
            print(green_bold('--------------------------------------------------------------\n'))
        except ValueError as e:
            print(e)
            # Handle the error as needed, possibly exiting the script
    else:
        # If app_id is not provided, print details for starting a new project
        print(green_bold('\n------------------ STARTING NEW PROJECT ----------------------'))
        print("If you wish to continue with this project in future run:")
        print(green_bold(f'python {sys.argv[0]} app_id={arguments.app_id}'))
        print(green_bold('--------------------------------------------------------------\n'))

    # Return the parsed arguments

    return arguments

def get_email():
    # Attempt to get email from .gitconfig
    gitconfig_path = os.path.expanduser('~/.gitconfig')

def get_email():
    # Attempt to get email from .gitconfig
    gitconfig_path = os.path.expanduser('~/.gitconfig')

    if os.path.exists(gitconfig_path):
        with open(gitconfig_path, 'r') as file:
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