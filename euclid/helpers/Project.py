from const.common import IGNORE_FOLDERS
from helpers.cli import build_directory_tree
from helpers.agents.CodeMonkey import CodeMonkey
from helpers.agents.TechLead import TechLead
from helpers.agents.DevOps import DevOps
from helpers.agents.Developer import Developer
from helpers.agents.Architect import Architect
from helpers.agents.ProductOwner import ProductOwner

class Project:
    def __init__(self, args, name=None, description=None, user_stories=None, user_tasks=None, architecture=None, development_plan=None, current_step=None):
        self.args = args

        if current_step != None:
            self.current_step = current_step
        if name != None:
            self.name = name
        if description != None:
            self.description = description
        if user_stories != None:
            self.user_stories = user_stories
        if user_tasks != None:
            self.user_tasks = user_tasks
        if architecture != None:
            self.architecture = architecture
        if development_plan != None:
            self.development_plan = development_plan

    def start(self):
        self.project_manager = ProductOwner(self)
        self.high_level_summary = self.project_manager.get_project_description()
        self.user_stories = self.project_manager.get_user_stories()
        self.user_tasks = self.project_manager.get_user_tasks()

        self.architect = Architect(self)
        self.architecture = self.architect.get_architecture()

        self.tech_lead = TechLead(self)
        self.development_plan = self.tech_lead.create_development_plan()

        self.developer = Developer(self)
        self.developer.set_up_environment();
        
        self.developer.start_coding()

    def get_directory_tree(self):
        return build_directory_tree(self.root_path, ignore=IGNORE_FOLDERS)
    
    def get_files(self, files):
        files_with_content = []
        for file in files:
            files_with_content.append({
                "path": file,
                "content": open(file, 'r').read()
            })
        return files_with_content
