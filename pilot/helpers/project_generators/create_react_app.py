import os
import subprocess
from helpers.Project import Project
from .project_generator import project_generator


@project_generator(name='create-react-app',
                   language='JavaScript, TypeScript',
                   topics=['react', 'javascript', 'typescript'])
class CreateReactApp:
    """
    Creates a React web app using create-react-app.
    """

    def get_documentation_url(self):
        return 'https://create-react-app.dev/docs/getting-started'

    def create_new_project(self, project: Project):
        cmd = ['npx', 'create-react-app', project.name]

        # if (project.language == 'TypeScript'):
        #     cmd.append('--template typescript')

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
