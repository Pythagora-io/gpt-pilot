import json
import os
from pathlib import Path
import re
from typing import Tuple

from const.messages import CHECK_AND_CONTINUE, AFFIRMATIVE_ANSWERS, NEGATIVE_ANSWERS
from utils.style import color_yellow_bold, color_cyan, color_white_bold, color_green
from const.common import IGNORE_FOLDERS, STEPS
from database.database import delete_unconnected_steps_from, delete_all_app_development_data, update_app_status
from const.ipc import MESSAGE_TYPE
from prompts.prompts import ask_user
from helpers.exceptions.TokenLimitError import TokenLimitError
from utils.questionary import styled_text
from helpers.files import get_directory_contents, get_file_contents, clear_directory, update_file
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

from utils.telemetry import telemetry

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
        self.main_prompt = None
        self.files = []

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
        telemetry.start()
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
                should_overwrite_files = None
                while should_overwrite_files is None or should_overwrite_files.lower() not in AFFIRMATIVE_ANSWERS + NEGATIVE_ANSWERS:
                    print('yes/no', type='button')
                    should_overwrite_files = styled_text(
                        self,
                        f'Do you want to overwrite the dev step {self.args["skip_until_dev_step"]} code with system changes? Type y/n',
                        ignore_user_input_count=True
                    )

                    logger.info('should_overwrite_files: %s', should_overwrite_files)
                    if should_overwrite_files in NEGATIVE_ANSWERS:
                        break
                    elif should_overwrite_files in AFFIRMATIVE_ANSWERS:
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
            try:
                # TODO path is sometimes relative and sometimes absolute - fix at one point
                _, full_path = self.get_full_file_path(file_path, file_path)
                file_data = get_file_contents(full_path, self.root_path)
            except ValueError:
                file_data = {"path": file_path, "content": ''}

            files_with_content.append(file_data)
        return files_with_content

    def find_input_required_lines(self, file_content):
        """
        Parses the provided string (representing file content) and returns a list of tuples containing
        the line number and line content for lines that contain the text 'INPUT_REQUIRED'.

        :param file_content: The string content of the file.
        :return: A list of tuples (line number, line content).
        """
        lines_with_input_required = []
        lines = file_content.split('\n')

        for line_number, line in enumerate(lines, start=1):
            if 'INPUT_REQUIRED' in line:
                lines_with_input_required.append((line_number, line.strip()))

        return lines_with_input_required

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
        if full_path not in self.files:
            self.files.append(full_path)

        (File.insert(app=self.app, path=path, name=name, full_path=full_path)
         .on_conflict(
            conflict_target=[File.app, File.name, File.path],
            preserve=[],
            update={'name': name, 'path': path, 'full_path': full_path})
         .execute())

        if not self.skip_steps:
            inputs_required = self.find_input_required_lines(data['content'])
            for line_number, line_content in inputs_required:
                user_input = ''
                print(color_yellow_bold(f'Input required on line {line_number}:\n{line_content}') + '\n')
                while user_input.lower() not in AFFIRMATIVE_ANSWERS:
                    print('yes', type='button')
                    user_input = styled_text(
                        self,
                        f'Please open the file {data["path"]} on the line {line_number} and add the required input. Once you\'re done, type "y" to continue.',
                        ignore_user_input_count=True
                    )

    def get_full_file_path(self, file_path: str, file_name: str) -> Tuple[str, str]:
        """
        Combine file path and name into a full file path.

        :param file_path: File path.
        :param file_name: File name.
        :return: (file_path, absolute_path) pair.

        Tries to combine the two in a way that makes most sense, even if the given path
        have some shared components.
        """
        def normalize_path(path: str) -> Tuple[str, str]:
            """
            Normalizes a path (see rules in comments) and returns (directory, basename) pair.

            :param path: Path to normalize.
            :return: (directory, basename) pair.

            Directory component may be empty if the path is considered to be a
            file name. Basename component may be empty if the path is considered
            to be a directory name.
            """

            # Normalize path to use os-specific separator (as GPT may output paths
            # with / even if we're on Windows)
            path = str(Path(path))

            # If a path references user's home directory (~), we only care about
            # the relative part within it (assume ~ is meant to be the project path).
            # Examples:
            # - /Users/zvonimirsabljic/Development/~/pilot/server.js -> /pilot/server.js
            # - ~/pilot/server.js -> /pilot/server.js
            if "~" in path:
                path = path.split("~")[-1]

            # If the path explicitly references the current directory, remove it so we
            # can nicely use it for joins later.
            if path == "." or path.startswith(f".{os.path.sep}"):
                path = path[1:]

            # If the path is absolute, we only care about the relative part within
            # the project directory (assume the project directory is the root).
            # Examples:
            # - /Users/zvonimirsabljic/Development/copilot/pilot/server.js -> /pilot/server.js
            # - /pilot/server.js -> /pilot/server.js
            # - C:\Users\zvonimirsabljic\Development\copilot\pilot\server.js -> \pilot\server.js
            path = path.replace(self.root_path, '')

            # If the final component of the path doesn't have a file extension,
            # assume it's a directory and add a final (back)slash.
            # Examples:
            # - /pilot/server.js -> /pilot/server.js
            # - /pilot -> /pilot/
            # - \pilot\server.js -> \pilot\server.js
            # - \pilot -> \pilot\
            base = os.path.basename(path)
            if base and "." not in base:
                path += os.path.sep

            # In case we're in Windows and dealing with full paths, remove the drive letter.
            _, path = os.path.splitdrive(path)

            # We want all paths to start with / (or \\ in Windows)
            if not path.startswith(os.path.sep):
                path = os.path.sep + path

            return os.path.split(path)

        head_path, tail_path = normalize_path(file_path)
        head_name, tail_name = normalize_path(file_name)

        # Prefer directory path from the first argument (file_path), and
        # prefer the file name from the second argument (file_name).
        final_file_path = head_path if head_path != '' else head_name
        final_file_name = tail_name if tail_name != '' else tail_path

        # If the directory is contained in the second argument (file_name),
        # use that (as it might include additional subdirectories).
        if head_path in head_name:
            final_file_path = head_name

        # Try to combine the directory and file name from the two arguments
        # in the way that makes the most sensible output.
        if final_file_path != head_name and head_name not in head_path:
            if '.' in tail_path:
                final_file_path = head_name + head_path
            else:
                final_file_path = head_path + head_name

        if final_file_path == '':
            final_file_path = os.path.sep

        final_absolute_path = os.path.join(self.root_path, final_file_path[1:], final_file_name)
        return final_file_path, final_absolute_path


    def save_files_snapshot(self, development_step_id):
        files = get_directory_contents(self.root_path, ignore=IGNORE_FOLDERS)
        development_step, created = DevelopmentSteps.get_or_create(id=development_step_id)

        for file in files:
            print(color_cyan(f'Saving file {file["full_path"]}'))
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

        clear_directory(self.root_path, IGNORE_FOLDERS + self.files)
        for file_snapshot in file_snapshots:
            update_file(file_snapshot.file.full_path, file_snapshot.content)
            if file_snapshot.file.full_path not in self.files:
                self.files.append(file_snapshot.file.full_path)

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

        while answer.lower() != 'continue':
            print('continue', type='button')
            answer = ask_user(self, CHECK_AND_CONTINUE,
                              require_some_input=False,
                              hint=question)

            try:
                if answer.lower() in cbs:
                    return cbs[answer.lower()](convo)
                elif answer != '':
                    return {'user_input': answer}
            except TokenLimitError as e:
                if is_root_task and answer.lower() not in cbs and answer != '':
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
