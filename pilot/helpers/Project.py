import json
import os
from pathlib import Path
from typing import Tuple

import peewee
from playhouse.shortcuts import model_to_dict

from const.messages import CHECK_AND_CONTINUE, AFFIRMATIVE_ANSWERS, NEGATIVE_ANSWERS, STUCK_IN_LOOP
from utils.style import color_yellow_bold, color_cyan, color_white_bold, color_red_bold
from const.common import STEPS
from database.database import delete_unconnected_steps_from, delete_all_app_development_data, \
    get_all_app_development_steps, delete_all_subsequent_steps, get_features_by_app_id
from const.ipc import MESSAGE_TYPE
from prompts.prompts import ask_user
from helpers.exceptions import TokenLimitError, GracefulExit
from utils.questionary import styled_text
from helpers.files import get_directory_contents, get_file_contents, clear_directory, update_file
from helpers.cli import build_directory_tree
from helpers.agents.TechLead import TechLead
from helpers.agents.Developer import Developer
from helpers.agents.Architect import Architect
from helpers.agents.ProductOwner import ProductOwner
from helpers.agents.TechnicalWriter import TechnicalWriter
from helpers.agents.SpecWriter import SpecWriter

from database.models.development_steps import DevelopmentSteps
from database.models.file_snapshot import FileSnapshot
from database.models.files import File
from logger.logger import logger
from utils.dot_gpt_pilot import DotGptPilot
from utils.llm_connection import test_api_access
from utils.ignore import IgnoreMatcher

from utils.telemetry import telemetry
from utils.task import Task
from utils.utils import remove_lines_with_string


class Project:
    def __init__(
        self,
        args,
        *,
        ipc_client_instance=None,
    ):
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
        self.current_task = Task()
        self.checkpoints = {
            'last_user_input': None,
            'last_command_run': None,
            'last_development_step': None,
        }
        # TODO make flexible
        self.root_path = ''
        self.skip_until_dev_step = self.args['skip_until_dev_step'] if 'skip_until_dev_step' in self.args else None
        self.skip_steps = False
        self.main_prompt = None
        self.files = []
        self.continuing_project = args.get('continuing_project', False)

        self.ipc_client_instance = ipc_client_instance

        self.finished = False
        self.current_step = None
        self.name = None
        self.project_description = None
        self.user_stories = None
        self.user_tasks = None
        self.architecture = ""
        self.system_dependencies = []
        self.package_dependencies = []
        self.project_template = None
        self.development_plan = None
        self.previous_features = None
        self.current_feature = None
        self.dot_pilot_gpt = DotGptPilot(log_chat_completions=True)

        if os.getenv("AUTOFIX_FILE_PATHS", "").lower() in ["true", "1", "yes"]:
            File.update_paths()

        # start loading of project (since backwards compatibility)
        self.should_overwrite_files = False
        self.last_detailed_user_review_goal = None
        self.last_iteration = None
        self.tasks_to_load = []
        self.features_to_load = []
        self.dev_steps_to_load = []
        if self.continuing_project:
            self.setup_loading()
        # end loading of project

    def set_root_path(self, root_path: str):
        self.root_path = root_path
        self.dot_pilot_gpt.with_root_path(root_path)

    def setup_loading(self):
        if self.skip_until_dev_step == '0':
            clear_directory(self.root_path)
            delete_all_app_development_data(self.args['app_id'])
            self.finish_loading(False)
            return

        self.skip_steps = True
        should_overwrite_files = None
        while should_overwrite_files is None or should_overwrite_files.lower() not in AFFIRMATIVE_ANSWERS + NEGATIVE_ANSWERS:
            print('Use GPT Pilot\'s code/Keep my changes', type='buttons-only')
            should_overwrite_files = styled_text(
                self,
                "Can GPT Pilot overwrite code changes you made since last running GPT Pilot?",
                ignore_user_input_count=True
            )

            logger.info('should_overwrite_files: %s', should_overwrite_files)
            if should_overwrite_files in NEGATIVE_ANSWERS:
                self.should_overwrite_files = False
                break
            elif should_overwrite_files in AFFIRMATIVE_ANSWERS:
                self.should_overwrite_files = True
                break

        load_step_before_coding = ('step' in self.args and
                                   self.args['step'] is not None and
                                   STEPS.index(self.args['step']) < STEPS.index('coding'))

        if load_step_before_coding:
            if not self.should_overwrite_files:
                print(color_red_bold('Cannot load step before "coding" without overwriting files. You have to reload '
                                     'the app and select "Use GPT Pilot\'s code" but you will lose all coding progress'
                                     ' on this project.'))
                raise GracefulExit()

            clear_directory(self.root_path)
            delete_all_app_development_data(self.args['app_id'])
            return

        self.dev_steps_to_load = get_all_app_development_steps(self.args['app_id'], last_step=self.skip_until_dev_step)
        if self.dev_steps_to_load is not None and len(self.dev_steps_to_load):
            self.checkpoints['last_development_step'] = self.dev_steps_to_load[-1]
            self.tasks_to_load = [el for el in self.dev_steps_to_load if 'breakdown.prompt' in el.get('prompt_path', '')]
            self.features_to_load = [el for el in self.dev_steps_to_load if 'feature_plan.prompt' in el.get('prompt_path', '')]

    def start(self):
        """
        Start the project.
        """

        telemetry.start()
        telemetry.set("app_id", self.args["app_id"])

        if not test_api_access(self):
            return False

        self.project_manager = ProductOwner(self)
        self.spec_writer = SpecWriter(self)

        self.project_manager.get_project_description(self.spec_writer)
        self.project_manager.get_user_stories()
        # self.user_tasks = self.project_manager.get_user_tasks()

        self.architect = Architect(self)
        self.architect.get_architecture()

        self.developer = Developer(self)
        self.developer.set_up_environment()
        self.technical_writer = TechnicalWriter(self)

        self.tech_lead = TechLead(self)
        self.tech_lead.create_development_plan()

        telemetry.set("architecture", {
            "description": self.architecture,
            "system_dependencies": self.system_dependencies,
            "package_dependencies": self.package_dependencies,
        })

        self.dot_pilot_gpt.write_project(self)
        print(json.dumps({
            "project_stage": "coding"
        }), type='info')
        self.developer.start_coding()
        return True

    def finish(self):
        """
        Finish the project.
        """
        while True:
            feature_description = ''
            if not self.features_to_load:
                self.finish_loading()

            self.previous_features = get_features_by_app_id(self.args['app_id'])
            if not self.skip_steps:
                feature_description = ask_user(self, "Project is finished! Do you want to add any features or changes? "
                                                     "If yes, describe it here and if no, just press ENTER",
                                               require_some_input=False)

                if feature_description == '':
                    return

                self.tech_lead.create_feature_plan(feature_description)

            # loading of features
            else:
                num_of_features = len(self.features_to_load)

                # last feature is always the one we want to load
                current_feature = self.features_to_load[-1]
                self.tech_lead.convo_feature_plan.messages = current_feature['messages'] + [{"role": "assistant", "content": current_feature['llm_response']['text']}]
                target_id = current_feature['id']
                self.cleanup_list('tasks_to_load', target_id)
                self.cleanup_list('dev_steps_to_load', target_id)

                # if there is feature_summary.prompt in remaining dev steps it means feature is fully done
                # finish loading and ask to add another feature or finish project
                feature_summary_dev_step = next((el for el in reversed(self.dev_steps_to_load) if 'feature_summary.prompt' in el.get('prompt_path', '')), None)
                if feature_summary_dev_step is not None:
                    self.cleanup_list('dev_steps_to_load', feature_summary_dev_step['id'])
                    self.finish_loading()
                    print(f'loaded {num_of_features} features')
                    continue


                print(f'Loaded {num_of_features - 1} features!')
                print(f'Continuing feature #{num_of_features}...')
                self.development_plan = json.loads(current_feature['llm_response']['text'])['plan']
                feature_description = current_feature['prompt_data']['feature_description']
                self.features_to_load = []

            self.current_feature = feature_description
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
        return build_directory_tree(self.root_path)

    def get_test_directory_tree(self):
        """
        Get the directory tree of the tests.

        Returns:
            dict: The directory tree of tests.
        """
        # TODO remove hardcoded path
        return build_directory_tree(self.root_path + '/tests')

    def get_files_from_db_by_step_id(self, step_id):
        """
        Get all coded files associated with a specific step_id.

        Args:
            step_id (int): The ID of the step.

        Returns:
            list: A list of coded files associated with the step_id.
        """
        if step_id is None:
            return []

        file_snapshots = FileSnapshot.select().where(FileSnapshot.development_step_id == step_id)

        return [{
            "name": item['file']['name'],
            "path": item['file']['path'],
            "full_path": item['file']['full_path'],
            'content': item['content'],
            "lines_of_code": len(item['content'].splitlines()),
        } for item in [model_to_dict(file) for file in file_snapshots]]

    def get_all_coded_files(self):
        """
        Get all coded files in the project.

        Returns:
            list: A list of coded files.
        """
        files = (
            File
            .select()
            .where(
                (File.app_id == self.args['app_id']) &
                peewee.fn.EXISTS(FileSnapshot.select().where(FileSnapshot.file_id == File.id))
            )
        )

        return self.get_files([file.path + '/' + file.name for file in files])

    def get_files(self, files):
        """
        Get file contents.

        Args:
            files (list): List of file paths.

        Returns:
            list: A list of files with content.
        """
        matcher = IgnoreMatcher(root_path=self.root_path)
        files_with_content = []
        for file_path in files:
            try:
                # TODO path is sometimes relative and sometimes absolute - fix at one point
                _, full_path = self.get_full_file_path(file_path, file_path)
                file_data = get_file_contents(full_path, self.root_path)
            except ValueError:
                full_path = None
                file_data = {"path": file_path, "name": os.path.basename(file_path), "content": ''}

            if full_path and file_data["content"] != "" and not matcher.ignore(full_path):
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
        update_file(full_path, data['content'], project=self)
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
                user_input = None
                print(color_yellow_bold(f'Input required on line {line_number}:\n{line_content}') + '\n')
                while user_input is None or user_input.lower() not in AFFIRMATIVE_ANSWERS + ['continue']:
                    print({'path': full_path, 'line': line_number}, type='openFile')
                    print('continue', type='buttons-only')
                    user_input = ask_user(
                        self,
                        f'Please open the file {data["path"]} on the line {line_number} and add the required input. Once you\'re done, type "y" to continue.',
                        require_some_input=False,
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
            KNOWN_FILES = ["makefile", "dockerfile", "procfile", "readme", "license"]  # known exceptions that break the heuristic
            KNOWN_DIRS = []  # known exceptions that break the heuristic
            base = os.path.basename(path)
            if (
                base
                and ("." not in base or base.lower() in KNOWN_DIRS)
                and base.lower() not in KNOWN_FILES
            ):
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
        files = get_directory_contents(self.root_path)
        development_step, created = DevelopmentSteps.get_or_create(id=development_step_id)

        total_files = 0
        total_lines = 0

        for file in files:
            if not self.check_ipc():
                print(color_cyan(f'Saving file {file["full_path"]}'))
            # TODO this can be optimized so we don't go to the db each time
            file_in_db, created = File.get_or_create(
                app=self.app,
                name=file['name'],
                path=file['path'],
                defaults={'full_path': file['full_path']},
            )

            file_snapshot, created = FileSnapshot.get_or_create(
                app=self.app,
                development_step=development_step,
                file=file_in_db,
                defaults={'content': file.get('content', '')}
            )
            file_snapshot.content = file['content']
            file_snapshot.save()
            total_files += 1
            if isinstance(file['content'], str):
                total_lines += file['content'].count('\n') + 1

        telemetry.set("num_files", total_files)
        telemetry.set("num_lines", total_lines)

    def restore_files(self, development_step_id):
        development_step = DevelopmentSteps.get(DevelopmentSteps.id == development_step_id)
        file_snapshots = FileSnapshot.select().where(FileSnapshot.development_step == development_step)

        clear_directory(self.root_path, ignore=self.files)
        for file_snapshot in file_snapshots:
            update_file(file_snapshot.file.full_path, file_snapshot.content, project=self)
            if file_snapshot.file.full_path not in self.files:
                self.files.append(file_snapshot.file.full_path)

    def delete_all_steps_except_current_branch(self):
        delete_unconnected_steps_from(self.checkpoints['last_development_step'], 'previous_step')
        delete_unconnected_steps_from(self.checkpoints['last_command_run'], 'previous_step')
        delete_unconnected_steps_from(self.checkpoints['last_user_input'], 'previous_step')

    def ask_for_human_intervention(self, message, description=None, cbs={}, convo=None, is_root_task=False, add_loop_button=False):
        answer = ''
        question = color_yellow_bold(message)

        if description is not None:
            question += '\n' + '-' * 100 + '\n' + color_white_bold(description) + '\n' + '-' * 100 + '\n'

        reset_branch_id = None if convo is None else convo.save_branch()

        while answer.lower() != 'continue':
            print('continue' + (f'/{STUCK_IN_LOOP}' if add_loop_button else ''), type='button')
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
        if self.check_ipc():
            self.ipc_client_instance.send({
                'type': MESSAGE_TYPE[message_type],
                'content': str(text),
            })
            if message_type == MESSAGE_TYPE['user_input_request']:
                return self.ipc_client_instance.listen()
        else:
            print(text)

    def check_ipc(self):
        """
        Checks if there is an open Inter-Process Communication (IPC) connection.

        Returns:
            bool: True if there is an open IPC connection, False otherwise.
        """
        return self.ipc_client_instance is not None and self.ipc_client_instance.client is not None

    def finish_loading(self, do_cleanup=True):
        # if already done, don't do it again
        if not self.skip_steps:
            return

        print('', type='loadingFinished')
        if do_cleanup and self.checkpoints['last_development_step']:
            if self.should_overwrite_files:
                self.restore_files(self.checkpoints['last_development_step']['id'])
            else:
                FileSnapshot.delete().where(
                    FileSnapshot.app == self.app and FileSnapshot.development_step == int(self.checkpoints['last_development_step']['id'])).execute()
                self.save_files_snapshot(int(self.checkpoints['last_development_step']['id']))
            delete_all_subsequent_steps(self)

        self.tasks_to_load = []
        self.features_to_load = []
        self.dev_steps_to_load = []
        self.last_detailed_user_review_goal = None
        self.last_iteration = None
        self.skip_steps = False

    def cleanup_list(self, list_name, target_id):
        if target_id is None or list_name is None:
            return

        temp_list = getattr(self, list_name, [])

        # Find the index of the first el with 'id' greater than target_id
        index = next((i for i, el in enumerate(temp_list) if el['id'] >= target_id), len(temp_list))

        new_list = temp_list[index:]

        if list_name == 'dev_steps_to_load' and len(new_list) == 0:
            # needed for finish_loading() because then we restore files, and we need last dev step
            self.checkpoints['last_development_step'] = temp_list[index - 1]

        # Keep only the elements from that index onwards
        setattr(self, list_name, new_list)

    def remove_debugging_logs_from_all_files(self):
        project_files = self.get_all_coded_files()
        for file in project_files:
            if 'gpt_pilot_debugging_log' in file['content'].lower():
                # remove all lines that contain 'debugging_log'
                file['content'] = remove_lines_with_string(file['content'], 'gpt_pilot_debugging_log')
                self.save_file(file)
