from const.function_calls import GET_DOCUMENTATION_FILE
from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from utils.files import count_lines_of_code
from utils.style import color_green_bold, color_green


class TechnicalWriter(Agent):
    def __init__(self, project):
        super().__init__('technical_writer', project)
        self.save_dev_steps = True

    def document_project(self, percent):
        files = self.project.get_all_coded_files()
        print(f'{color_green_bold("CONGRATULATIONS!!!")}')
        print(f'You reached {color_green(str(percent) + "%")} of your project generation!\n\n')
        print('For now, you have created:\n')
        print(f'{color_green(len(files))} files\n')
        print(f'{color_green(count_lines_of_code(files))} lines of code\n\n')
        print('Before continuing, GPT Pilot will create some documentation for the project...\n')
        self.create_license()
        self.create_readme()
        self.create_api_documentation()

    def create_license(self):
        # check if LICENSE file exists and if not create one. We want to create it only once.
        return

    def create_readme(self):
        print(color_green('Creating README.md'))
        convo = AgentConvo(self)

        llm_response = convo.send_message('documentation/create_readme.prompt', {
            "name": self.project.args['name'],
            "app_type": self.project.args['app_type'],
            "app_summary": self.project.project_description,
            "user_stories": self.project.user_stories,
            "user_tasks": self.project.user_tasks,
            "directory_tree": self.project.get_directory_tree(True),
            "files": self.project.get_all_coded_files(),
            "previous_features": self.project.previous_features,
            "current_feature": self.project.current_feature,
        }, GET_DOCUMENTATION_FILE)

        self.project.save_file(llm_response)
        return convo

    def create_api_documentation(self):
        # create API documentation
        return
