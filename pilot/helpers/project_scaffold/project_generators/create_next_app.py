import os
import subprocess
from .project_generator import project_generator


@project_generator(name='create-next-app',
                   language='JavaScript, TypeScript',
                   topics=['Next.js', 'javascript', 'typescript'])
class CreateNextApp:
    """
    Creates a Next.JS web app using create-next-app.
    """

    def describe_options(self):
        return {
            'typescript': {
                'description': 'Initialize as a TypeScript project',
                'type': 'boolean',
                # 'default': true
            },
            'javascript': {
                'description': 'Initialize as a JavaScript project',
                'type': 'boolean',
            },
            'tailwind': {
                'description': 'Initialize with Tailwind CSS config',
                'type': 'boolean',
            },
            'eslint': {
                'description': 'Initialize with ESLint config',
                'type': 'boolean',
            },
            'app': {
                'description': 'Initialize as an App Router project',
                'type': 'boolean',
            },
            # 'src-dir': {
            #     'description': 'Initialize inside a `src/` directory',
            # },
            'import-alias': {
                'description': 'Specify import alias to use (default "@/*")',
                'type': 'string',
            },
            'use-npm': {
                'description': 'Explicitly tell the CLI to bootstrap the app using npm',
                'type': 'boolean',
            },
            'example': {
                'description': 'An example to bootstrap the app with. You can use an example name '
                               'from the official Next.js repo or a public GitHub URL. The URL can use '
                               'any branch and/or subdirectory'
            },
            'example-path': {
                'description': 'In a rare case, your GitHub URL might contain a branch name with '
                               'a slash (e.g. bug/fix-1) and the path to the example (e.g. foo/bar). '
                               'In this case, you must specify the path to the example separately: '
                               '--example-path foo/bar'
            },
        }

    def create_new_project(self, project):
        cmd = ['npx', 'create-next-app', project.name]

        cmd += ['--yes']

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
