import os
from pathlib import Path
from database.database import save_user_app


def get_parent_folder(folder_name):
    current_path = Path(os.path.abspath(__file__))  # get the path of the current script

    while current_path.name != folder_name:  # while the current folder name is not 'folder_name'
        current_path = current_path.parent  # go up one level

    return current_path.parent


def setup_workspace(args) -> str:
    """
    Creates & returns the path to the project workspace.
    Also creates a 'tests' folder inside the workspace.
    :param args: may contain 'root' key
    """
    root = args.get('root') or get_parent_folder('pilot')
    name = args.get('name', 'default_project_name')
    project_path = create_directory(os.path.join(root, 'workspace'), name)
    create_directory(project_path, 'tests')
    try:
        save_user_app(args.get('user_id'), args.get('app_id'), name)
    except Exception as e:
        print(str(e))

    return project_path


def create_directory(parent_directory, new_directory):
    new_directory_path = os.path.join(parent_directory, new_directory)
    os.makedirs(new_directory_path, exist_ok=True)

    return new_directory_path
