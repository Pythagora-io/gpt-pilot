import os
import subprocess
from helpers.Project import Project
from .project_generator import project_generator


@project_generator(name='create-next-app',
                   language='JavaScript, TypeScript',
                   topics=['Next.js', 'javascript', 'typescript'])
class CreateNextApp:
    """
    Creates a Next.JS web app using create-next-app.
    """

    def create_new_project(self, project: Project):
        cmd = ['npx', 'create-next-app', project.name]

        # if (project.language == 'TypeScript'):
        #     cmd.append('--template typescript')

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
