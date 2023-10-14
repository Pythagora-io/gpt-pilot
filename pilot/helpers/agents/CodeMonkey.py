from const.function_calls import GET_FILES, IMPLEMENT_CHANGES
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent


class CodeMonkey(Agent):
    def __init__(self, project, developer):
        super().__init__('code_monkey', project)
        self.developer = developer

    def implement_code_changes(self, convo, code_changes_description, step_index=0):
        if convo is None:
            convo = AgentConvo(self)

        # files_needed = convo.send_message('development/task/request_files_for_code_changes.prompt', {
        #     "step_description": code_changes_description,
        #     "directory_tree": self.project.get_directory_tree(True),
        #     "step_index": step_index,
        #     "finished_steps": ', '.join(f"#{j}" for j in range(step_index))
        # }, GET_FILES)

        llm_response = convo.send_message('development/implement_changes.prompt', {
            "step_description": code_changes_description,
            "step_index": step_index,
            "directory_tree": self.project.get_directory_tree(True),
            "files": []  # self.project.get_files(files_needed),
        }, IMPLEMENT_CHANGES)
        convo.remove_last_x_messages(1)

        changes = llm_response['files']

        if self.project.skip_until_dev_step != str(self.project.checkpoints['last_development_step'].id):
            for file_data in changes:
                self.project.save_file(file_data)

        return convo
