import os
import subprocess
from helpers.Project import Project
from .project_generator import project_generator


@project_generator(name='create-expo-app',
                   language='JavaScript, TypeScript',
                   topics=['react native', 'javascript', 'typescript', 'mobile', 'android', 'ios', 'expo'])
class CreateExpoApp:
    """
    Creates a React Native app for Android or iOS devices using create-expo-app.
    """

    # TODO: https://github.com/expo/examples refers to `create-react-native-app`?
    # TODO: npx react-native init project.nam

    def get_documentation_url(self):
        return 'https://docs.expo.dev/tutorial/create-your-first-app'

    def create_new_project(self, project: Project):
        cmd = ['npx', 'create-expo-app', project.name]

        # if (project.language == 'TypeScript'):
        #     cmd.append('--template typescript')

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
