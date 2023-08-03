from const.function_calls import GET_FILES, DEV_STEPS, IMPLEMENT_CHANGES, CODE_CHANGES
from helpers.files import update_file
from helpers.cli import run_command_until_success
from helpers.cli import build_directory_tree
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent

class CodeMonkey(Agent):
    def __init__(self, project, developer):
        super().__init__('code_monkey', project)
        self.developer = developer

    def implement_code_changes(self, convo, code_changes_description, step_index):
        if convo == None:
            convo = AgentConvo(self)

        files_needed = convo.send_message('development/task/request_files_for_code_changes.prompt', {
            "step_description": code_changes_description,
            "directory_tree": self.project.get_directory_tree(),
            "step_index": step_index,
            "finished_steps": ', '.join(f"#{j}" for j in range(step_index))
        }, GET_FILES)


        changes = convo.send_message('development/implement_changes.prompt', {
            "instructions": code_changes_description,
            "directory_tree": self.project.get_directory_tree(),
            "files": self.project.get_files(files_needed),
        }, IMPLEMENT_CHANGES)

        for file_data in changes:
            update_file(self.project.get_full_file_path(file_data['name']), file_data['content'])

        return convo
