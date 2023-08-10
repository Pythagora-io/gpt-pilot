import os

from termcolor import colored
from const.common import IGNORE_FOLDERS
from database.models.app import App
from database.database import get_app, delete_unconnected_steps_from
from utils.questionary import styled_text
from helpers.files import get_files_content, clear_directory
from helpers.cli import build_directory_tree
from helpers.agents.TechLead import TechLead
from helpers.agents.Developer import Developer
from helpers.agents.Architect import Architect
from helpers.agents.ProductOwner import ProductOwner

from database.models.development_steps import DevelopmentSteps
from database.models.file_snapshot import FileSnapshot
from database.models.files import File
from utils.files import get_parent_folder


class Project:
    def __init__(self, args, name=None, description=None, user_stories=None, user_tasks=None, architecture=None,
                 development_plan=None, current_step=None):
        self.args = args
        self.llm_req_num = 0
        self.command_runs_count = 0
        self.user_inputs_count = 0
        self.checkpoints = {
            'last_user_input': None,
            'last_command_run': None,
            'last_development_step': None,
        }
        self.skip_steps = False if ('skip_until_dev_step' in args and args['skip_until_dev_step'] == '0') else True
        self.skip_until_dev_step = args['skip_until_dev_step'] if 'skip_until_dev_step' in args else None
        # TODO make flexible
        # self.root_path = get_parent_folder('euclid')
        self.root_path = ''
        # self.restore_files({dev_step_id_to_start_from})

        if current_step is not None:
            self.current_step = current_step
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if user_stories is not None:
            self.user_stories = user_stories
        if user_tasks is not None:
            self.user_tasks = user_tasks
        if architecture is not None:
            self.architecture = architecture
        if development_plan is not None:
            self.development_plan = development_plan

    def start(self):
        self.project_manager = ProductOwner(self)
        self.project_manager.get_project_description()
        self.user_stories = self.project_manager.get_user_stories()
        self.user_tasks = self.project_manager.get_user_tasks()

        self.architect = Architect(self)
        self.architecture = self.architect.get_architecture()

        self.tech_lead = TechLead(self)
        self.development_plan = self.tech_lead.create_development_plan()

        self.developer = Developer(self)
        self.developer.set_up_environment();

        self.developer.start_coding()

    def get_directory_tree(self, with_descriptions=False):
        files = {}
        if with_descriptions:
            files = File.select().where(File.app_id == self.args['app_id'])
            files = {snapshot.name: snapshot for snapshot in files}
        return build_directory_tree(self.root_path + '/', ignore=IGNORE_FOLDERS, files=files, add_descriptions=True)

    def get_test_directory_tree(self):
        # TODO remove hardcoded path
        return build_directory_tree(self.root_path + '/tests', ignore=IGNORE_FOLDERS)

    def get_files(self, files):
        files_with_content = []
        for file in files:
            # TODO this is a hack, fix it
            try:
                file_content = open(self.get_full_file_path('', file), 'r').read()
            except:
                file_content = ''

            files_with_content.append({
                "path": file,
                "content": file_content
            })
        return files_with_content

    def get_full_file_path(self, file_path, file_name):
        file_path = file_path.replace('./', '', 1).rstrip(file_name)
        if not file_path.endswith('/'):
            file_path = file_path + '/'
        return self.root_path + file_path + file_name

    def save_files_snapshot(self, development_step_id):
        files = get_files_content(self.root_path, ignore=IGNORE_FOLDERS)
        development_step, created = DevelopmentSteps.get_or_create(id=development_step_id)

        for file in files:
            file_snapshot, created = FileSnapshot.get_or_create(
                development_step=development_step,
                name=file['name'],
                defaults={'content': file.get('content', '')}
            )
            file_snapshot.content = content = file['content']
            file_snapshot.save()

    def restore_files(self, development_step_id):
        development_step = DevelopmentSteps.get(DevelopmentSteps.id == development_step_id)
        file_snapshots = FileSnapshot.select().where(FileSnapshot.development_step == development_step)

        clear_directory(self.root_path, IGNORE_FOLDERS)
        for file_snapshot in file_snapshots:
            full_path = self.root_path + '/' + file_snapshot.name
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write/overwrite the file with its content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file_snapshot.content)

    def delete_all_steps_except_current_branch(self):
        delete_unconnected_steps_from(self.checkpoints['last_development_step'], 'previous_step')
        delete_unconnected_steps_from(self.checkpoints['last_command_run'], 'previous_step')
        delete_unconnected_steps_from(self.checkpoints['last_user_input'], 'previous_step')

    def ask_for_human_intervention(self, message, description):
        print(colored(message, "yellow"))
        print(description)
        answer = ''
        while answer != 'continue':
            answer = styled_text(
                self,
                'Once you are ready, type "continue" to continue.',
            )
