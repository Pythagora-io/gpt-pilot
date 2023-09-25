import os
import subprocess
from .project_generator import project_generator


@project_generator(name='create vite',
                   language='JavaScript, TypeScript',
                   topics=['vite', 'javascript', 'typescript',
                           'vanilla javascript', 'vue', 'react', 'preact', 'lit', 'svelte', 'solid-js'])
class CreateVite:
    """
    Creates a new web app using create-vite.
    """

    def create_new_project(self, project):
        cmd = ['npx', 'create vite', project.name]

        # TODO: Architect suggest and user confirms from front-end options:
        #  'vanilla javascript', 'vue', 'react', 'preact', 'lit', 'svelte', 'solid'
        # See also https://github.com/vitejs/awesome-vite#templates
        template = 'react'

        # if (project.language == 'TypeScript'):
        #     template += '-ts'

        cmd.append(f'--template {template}')

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
