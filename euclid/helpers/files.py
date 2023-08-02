from termcolor import colored
import os

from database.models.development_steps import DevelopmentSteps
from database.models.file_snapshot import FileSnapshot


def update_file(path, new_content):
    with open(path, 'w') as file:
        file.write(new_content)
        print(colored(f"Updated file {path}", "green"))

def get_files_content(directory, ignore=[]):
    return_array = []

    for root, dirs, files in os.walk(directory):
        # Ignore directories
        dirs[:] = [d for d in dirs if d not in ignore]

        for file in files:
            if file in ignore:
                continue

            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()

            return_array.append({
                'name': path.replace(directory + '/', ''),
                'content': file_content
            })

    return return_array

