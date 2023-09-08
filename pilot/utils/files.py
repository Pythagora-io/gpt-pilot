import os
from pathlib import Path


def get_parent_folder(folder_name):
    current_path = Path(os.path.abspath(__file__))  # get the path of the current script

    while current_path.name != folder_name:  # while the current folder name is not 'folder_name'
        current_path = current_path.parent  # go up one level

    return current_path.parent


def setup_workspace(args):
    if args['workspace'] is not None:
        return args['workspace']

    root = get_parent_folder('pilot')
    create_directory(root, 'workspace')
    project_path = create_directory(os.path.join(root, 'workspace'), args['name'])
    create_directory(project_path, 'tests')
    return project_path


def create_directory(parent_directory, new_directory):
    new_directory_path = os.path.join(parent_directory, new_directory)
    os.makedirs(new_directory_path, exist_ok=True)

    return new_directory_path
