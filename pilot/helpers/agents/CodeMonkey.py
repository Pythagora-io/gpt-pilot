from const.function_calls import READ_WRITE_FILES, IMPLEMENT_CHANGES
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

    def create_project_scripts(self):
        convo = AgentConvo(self)
        llm_response = convo.send_message('development/scripts.prompt',
            {
                "app_type": self.project.args['app_type'],
                "technologies": self.project.architecture,
                'directory_tree': self.project.get_directory_tree(True),
            }, READ_WRITE_FILES)

        # TODO: this code could be shared by other agents who want to read/write files
        files_written = False
        while True:
            for file in llm_response['files']:
                if isinstance(file, dict):
                    # Write content to file path
                    self.project.save_file(file)
                    files_written = True
                else:
                    # Reading files by path
                    content = self.project.get_file_content(file, default_content=None)
                    if content is not None:
                        content = f'{file}:\n```\n{content}\n```'
                    else:
                        content = f'The file "{file}" does not exist.'
                        # if file.endswith('.md'):
                        #     content += f' [DIRECTIVE] Instead of using `read_files` create a new file named `{file}` using the provided template.'

                    # TODO: if the LLM asks for too many files and the context is too large, add a `scratch pad` field to the `get_files` function and replace the last convo.message
                    convo.messages.append({'role': 'user', 'content': content})

            if files_written:
                break
            llm_response = convo.send_message(None, None, READ_WRITE_FILES)
