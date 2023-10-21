import json
import os
import re
from typing import Tuple
from utils.style import color_yellow_bold, color_cyan, color_white_bold, color_green
from const.common import IGNORE_FOLDERS, STEPS
from database.database import delete_unconnected_steps_from, delete_all_app_development_data, update_app_status
from const.ipc import MESSAGE_TYPE
from prompts.prompts import ask_user
from helpers.exceptions.TokenLimitError import TokenLimitError
from utils.questionary import styled_text
from helpers.files import get_files_content, clear_directory, update_file
from helpers.cli import build_directory_tree
from helpers.agents.TechLead import TechLead
from helpers.agents.Developer import Developer
from helpers.agents.Architect import Architect
from helpers.agents.ProductOwner import ProductOwner

from database.models.development_steps import DevelopmentSteps
from database.models.file_snapshot import FileSnapshot
from database.models.files import File
from logger.logger import logger
from utils.dot_gpt_pilot import DotGptPilot


class Project:
    def __init__(self, args, name=None, project_description=None, clarifications=None, user_stories=None,
                 user_tasks=None, architecture=None, development_plan=None, current_step=None, ipc_client_instance=None,
                 enable_dot_pilot_gpt=True):
        """
        Initialize a project.

        Args:
            args (dict): Project arguments - app_id, (app_type, name), user_id, email, password, step
            name (str, optional): Project name. Default is None.
            description (str, optional): Project description. Default is None.
            user_stories (list, optional): List of user stories. Default is None.
            user_tasks (list, optional): List of user tasks. Default is None.
            architecture (str, optional): Project architecture. Default is None.
            development_plan (str, optional): Development plan. Default is None.
            current_step (str, optional): Current step in the project. Default is None.
        """
        self.args = args
        self.llm_req_num = 0
        self.command_runs_count = 0
        self.user_inputs_count = 0
        self.checkpoints = {
            'last_user_input': None,
            'last_command_run': None,
            'last_development_step': None,
        }
        # TODO make flexible
        self.root_path = ''
        self.skip_until_dev_step = None
        self.skip_steps = None

        self.ipc_client_instance = ipc_client_instance

        # self.restore_files({dev_step_id_to_start_from})

        self.finished = args.get('status') == 'finished'
        self.current_step = current_step
        self.name = name
        self.project_description = project_description
        self.clarifications = clarifications
        self.user_stories = user_stories
        self.user_tasks = user_tasks
        self.architecture = architecture
        self.development_plan = development_plan
        self.dot_pilot_gpt = DotGptPilot(log_chat_completions=enable_dot_pilot_gpt)

    def set_root_path(self, root_path: str):
        self.root_path = root_path
        self.dot_pilot_gpt.with_root_path(root_path)

    def start(self):
        """
        Start the project.
        """
        self.project_manager = ProductOwner(self)
        self.project_manager.get_project_description()

        self.project_manager.get_user_stories()
        # self.user_tasks = self.project_manager.get_user_tasks()

        self.architect = Architect(self)
        self.architect.get_architecture()

        self.developer = Developer(self)
        self.developer.set_up_environment()

        self.tech_lead = TechLead(self)
        self.tech_lead.create_development_plan()

        if self.finished:  # once project is finished no need to load all development steps
            print(color_green("✅  Coding"))
            return

        # TODO move to constructor eventually
        if self.args['step'] is not None and STEPS.index(self.args['step']) < STEPS.index('coding'):
            clear_directory(self.root_path)
            delete_all_app_development_data(self.args['app_id'])
            self.skip_steps = False

        if 'skip_until_dev_step' in self.args:
            self.skip_until_dev_step = self.args['skip_until_dev_step']
            if self.args['skip_until_dev_step'] == '0':
                clear_directory(self.root_path)
                delete_all_app_development_data(self.args['app_id'])
                self.skip_steps = False
            elif self.skip_until_dev_step is not None:
                should_overwrite_files = ''
                while should_overwrite_files != 'y' or should_overwrite_files != 'n':
                    should_overwrite_files = styled_text(
                        self,
                        f'Do you want to overwrite the dev step {self.args["skip_until_dev_step"]} code with system changes? Type y/n',
                        ignore_user_input_count=True
                    )

                    logger.info('should_overwrite_files: %s', should_overwrite_files)
                    if should_overwrite_files == 'n':
                        break
                    elif should_overwrite_files == 'y':
                        FileSnapshot.delete().where(
                            FileSnapshot.app == self.app and FileSnapshot.development_step == self.skip_until_dev_step).execute()
                        self.save_files_snapshot(self.skip_until_dev_step)
                        break
        # TODO END

        self.dot_pilot_gpt.write_project(self)
        print(json.dumps({
            "project_stage": "coding"
        }), type='info')
        self.developer.start_coding()

    def finish(self):
        """
        Finish the project.
        """
        while True:
            feature_description = ask_user(self, "Project is finished! Do you want to add any features or changes? "
                                                 "If yes, describe it here and if no, just press ENTER",
                                           require_some_input=False)

            if feature_description == '':
                return

            self.tech_lead.create_feature_plan(feature_description)
            self.developer.start_coding()
            self.tech_lead.create_feature_summary(feature_description)

    def get_directory_tree(self, with_descriptions=False):
        """
        Get the directory tree of the project.

        Args:
            with_descriptions (bool, optional): Whether to include descriptions. Default is False.

        Returns:
            dict: The directory tree.
        """
        # files = {}
        # if with_descriptions and False:
        #     files = File.select().where(File.app_id == self.args['app_id'])
        #     files = {snapshot.name: snapshot for snapshot in files}
        # return build_directory_tree_with_descriptions(self.root_path, ignore=IGNORE_FOLDERS, files=files, add_descriptions=False)
        return build_directory_tree(self.root_path, ignore=IGNORE_FOLDERS)

    def get_test_directory_tree(self):
        """
        Get the directory tree of the tests.

        Returns:
            dict: The directory tree of tests.
        """
        # TODO remove hardcoded path
        return build_directory_tree(self.root_path + '/tests', ignore=IGNORE_FOLDERS)

    def get_all_coded_files(self):
        """
        Get all coded files in the project.

        Returns:
            list: A list of coded files.
        """
        files = File.select().where(File.app_id == self.args['app_id'])

        # TODO temoprary fix to eliminate files that are not in the project
        files = [file for file in files if len(FileSnapshot.select().where(FileSnapshot.file_id == file.id)) > 0]
        # TODO END

        files = self.get_files([file.path + '/' + file.name for file in files])

        # TODO temoprary fix to eliminate files that are not in the project
        files = [file for file in files if file['content'] != '']
        # TODO END

        return files

    def get_files(self, files):
        """
        Get file contents.

        Args:
            files (list): List of file paths.

        Returns:
            list: A list of files with content.
        """
        files_with_content = []
        for file_path in files:
            # TODO this is a hack, fix it
            try:
                name = os.path.basename(file_path)
                relative_path, full_path = self.get_full_file_path(file_path, name)
                file_content = open(full_path, 'r').read()
            except OSError:
                file_content = ''

            files_with_content.append({
                "path": file_path,
                "content": file_content
            })
        return files_with_content

    def save_file(self, data):
        """
        Save a file.

        Args:
            data: { name: 'hello.py', path: 'path/to/hello.py', content: 'print("Hello!")' }
        """
        name = data['name'] if 'name' in data and data['name'] != '' else os.path.basename(data['path'])
        path = data['path'] if 'path' in data else name

        path, full_path = self.get_full_file_path(path, name)
        update_file(full_path, data['content'])

        (File.insert(app=self.app, path=path, name=name, full_path=full_path)
         .on_conflict(
            conflict_target=[File.app, File.name, File.path],
            preserve=[],
            update={'name': name, 'path': path, 'full_path': full_path})
         .execute())

    def get_full_file_path(self, file_path: str, file_name: str) -> Tuple[str, str]:
        file_name = os.path.basename(file_name)

        if file_path.startswith(self.root_path):
            file_path = file_path.replace(self.root_path, '')

        if file_path == file_name:
            file_path = ''
        else:
            are_windows_paths = '\\' in file_path or '\\' in file_name or '\\' in self.root_path
            if are_windows_paths:
                file_path = file_path.replace('\\', '/')

            # Force all paths to be relative to the workspace
            file_path = re.sub(r'^(\w+:/|[/~.]+)', '', file_path, 1)

            # file_path should not include the file name
            if file_path == file_name:
                file_path = ''
            elif file_path.endswith('/' + file_name):
                file_path = file_path.replace('/' + file_name, '')
            elif file_path.endswith('/'):
                file_path = file_path[:-1]

        absolute_path = self.root_path + '/' + file_name if file_path == '' \
            else self.root_path + '/' + file_path + '/' + file_name

        return file_path, absolute_path

    def save_files_snapshot(self, development_step_id):
        files = get_files_content(self.root_path, ignore=IGNORE_FOLDERS)
        development_step, created = DevelopmentSteps.get_or_create(id=development_step_id)

        for file in files:
            print(color_cyan(f'Saving file {(file["path"])}/{file["name"]}'))
            # TODO this can be optimized so we don't go to the db each time
            file_in_db, created = File.get_or_create(
                app=self.app,
                name=file['name'],
                path=file['path'],
                full_path=file['full_path'],
            )

            file_snapshot, created = FileSnapshot.get_or_create(
                app=self.app,
                development_step=development_step,
                file=file_in_db,
                defaults={'content': file.get('content', '')}
            )
            file_snapshot.content = file['content']
            file_snapshot.save()

    def restore_files(self, development_step_id):
        development_step = DevelopmentSteps.get(DevelopmentSteps.id == development_step_id)
        file_snapshots = FileSnapshot.select().where(FileSnapshot.development_step == development_step)

        clear_directory(self.root_path, IGNORE_FOLDERS)
        for file_snapshot in file_snapshots:
            update_file(file_snapshot.file.full_path, file_snapshot.content)

    def delete_all_steps_except_current_branch(self):
        delete_unconnected_steps_from(self.checkpoints['last_development_step'], 'previous_step')
        delete_unconnected_steps_from(self.checkpoints['last_command_run'], 'previous_step')
        delete_unconnected_steps_from(self.checkpoints['last_user_input'], 'previous_step')

    def ask_for_human_intervention(self, message, description=None, cbs={}, convo=None, is_root_task=False):
        answer = ''
        question = color_yellow_bold(message)

        if description is not None:
            question += '\n' + '-' * 100 + '\n' + color_white_bold(description) + '\n' + '-' * 100 + '\n'

        reset_branch_id = None if convo is None else convo.save_branch()

        while answer != 'continue':
            answer = ask_user(self, question,
                              require_some_input=False,
                              hint='If something is wrong, tell me or type "continue" to continue.')

            try:
                if answer in cbs:
                    return cbs[answer](convo)
                elif answer != '':
                    return {'user_input': answer}
            except TokenLimitError as e:
                if is_root_task and answer not in cbs and answer != '':
                    convo.load_branch(reset_branch_id)
                    return {'user_input': answer}
                else:
                    raise e

    def log(self, text, message_type):
        if self.ipc_client_instance is None or self.ipc_client_instance.client is None:
            print(text)
        else:
            self.ipc_client_instance.send({
                'type': MESSAGE_TYPE[message_type],
                'content': str(text),
            })
            if message_type == MESSAGE_TYPE['user_input_request']:
                return self.ipc_client_instance.listen()
