from const.function_calls import GET_DOCUMENTATION_FILE
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from utils.files import count_lines_of_code


class TechnicalWriter(Agent):
    def __init__(self, project):
        super().__init__('technical_writer', project)

    def document_project(self, percent):
        files = self.project.get_all_coded_files()
        print(f'Congratulations, you reached {percent}% of your project generation!'
              f'For now, you have created:'
              f'{len(files)} files'
              f'{count_lines_of_code(files)} lines of code')
        print('Before continuing, GPT Pilot will create some documentation for the project...')
        self.create_license()
        self.create_readme()
        self.create_api_documentation()

    def create_license(self):
        # create LICENSE
        return

    def create_readme(self):
        print('Creating README.md')
        convo = AgentConvo(self)

        llm_response = convo.send_message('documentation/create_readme.prompt', {
            "name": self.project.args['name'],
            "app_type": self.project.args['app_type'],
            "app_summary": self.project.project_description,
            "clarifications": self.project.clarifications,
            "user_stories": self.project.user_stories,
            "user_tasks": self.project.user_tasks,
            "technologies": self.project.architecture,
            "directory_tree": self.project.get_directory_tree(True),
            "files": self.project.get_all_coded_files(),
        }, GET_DOCUMENTATION_FILE)

        # changes = self.project.developer.replace_old_code_comments([llm_response])
        #
        # if self.project.skip_until_dev_step != str(self.project.checkpoints['last_development_step'].id):
        #     for file_data in changes:
        #         self.project.save_file(file_data)

        self.project.save_file(llm_response)
        return convo

    def create_api_documentation(self):
        # create API documentation
        return


