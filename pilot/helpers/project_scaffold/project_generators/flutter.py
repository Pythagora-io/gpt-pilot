import os
import subprocess
from .project_generator import project_generator


@project_generator(name='flutter',
                   language='Dart, Kotlin, Swift',
                   topics=['Flutter', 'mobile', 'dart', 'kotlin', 'swift', 'android', 'ios',
                           'web', 'desktop', 'macos', 'windows', 'linux'])
class Flutter:
    """
    Creates a mobile, desktop or web app using Flutter.
    """

    def get_documentation_url(self):
        return 'https://docs.flutter.dev/reference/flutter-cli'

    def create_new_project(self, project):
        cmd = ['flutter', 'create', project.name]

        # if (project.language == 'TypeScript'):
        #     cmd.append('--template typescript')

        # Run the command
        os.chdir(os.path.pardir(project.root_path))
        subprocess.run(cmd)
        os.chdir(project.root_path)
