from const.function_calls import READ_WRITE_FILES, WRITE_FILES
from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo


class TechnicalWriter(Agent):
    def __init__(self, project):
        super().__init__('technical_writer', project)

    def document_project(self):
        convo = AgentConvo(self)
        content = self.project.get_file_content('README.md')

        llm_response = convo.send_message('project/document_project.prompt', {
            'name': self.project.args['name'],
            'app_type': self.project.args['app_type'],
            'project_description': self.project.project_description,
            'directory_tree': self.project.get_directory_tree(True),
            'readme': content,
        }, READ_WRITE_FILES)

        files_written = False
        while not files_written:
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
                        if file.endswith('.md'):
                            content += f' [DIRECTIVE] Instead of using `read_files` create a new file named `{file}` using the provided template.'

                    # TODO: if the LLM asks for too many files and the context is too large, add a `scratch pad` field to the `get_files` function and replace the last convo.message
                    convo.messages.append({'role': 'system', 'content': content})

            if files_written:
                break
            llm_response = convo.send_message(None, None, READ_WRITE_FILES)
