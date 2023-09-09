import hashlib
import os
import re
import sys
import uuid
from getpass import getuser
from termcolor import colored
from database.database import get_app, get_app_by_user_workspace


def get_arguments():
    # The first element in sys.argv is the name of the script itself.
    # Any additional elements are the arguments passed from the command line.
    args = sys.argv[1:]

    # Create an empty dictionary to store the key-value pairs.
    arguments = {}

    # Loop through the arguments and parse them as key-value pairs.
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            arguments[key] = value
        else:
            arguments[arg] = True

    if 'user_id' not in arguments:
        arguments['user_id'] = username_to_uuid(getuser())

    app = None
    if 'workspace' in arguments:
        app = get_app_by_user_workspace(arguments['user_id'], arguments['workspace'])
        if app is not None:
            arguments['app_id'] = app.id
    else:
        arguments['workspace'] = None

    if 'app_id' in arguments:
        try:
            if app is None:
                app = get_app(arguments['app_id'])

            arguments['app_type'] = app.app_type
            arguments['name'] = app.name
            # Add any other fields from the App model you wish to include

            print(colored('\n------------------ LOADING PROJECT ----------------------', 'green', attrs=['bold']))
            print(colored(f'{app.name} (app_id={arguments["app_id"]})', 'green', attrs=['bold']))
            print(colored('--------------------------------------------------------------\n', 'green', attrs=['bold']))
        except ValueError as e:
            print(e)
            # Handle the error as needed, possibly exiting the script
    else:
        arguments['app_id'] = str(uuid.uuid4())
        print(colored('\n------------------ STARTING NEW PROJECT ----------------------', 'green', attrs=['bold']))
        print("If you wish to continue with this project in future run:")
        print(colored(f'python {sys.argv[0]} app_id={arguments["app_id"]}', 'green', attrs=['bold']))
        print(colored('--------------------------------------------------------------\n', 'green', attrs=['bold']))

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
    sha1 = hashlib.sha1(username.encode()).hexdigest()
    uuid_str = "{}-{}-{}-{}-{}".format(sha1[:8], sha1[8:12], sha1[12:16], sha1[16:20], sha1[20:32])
    return str(uuid.UUID(uuid_str))
