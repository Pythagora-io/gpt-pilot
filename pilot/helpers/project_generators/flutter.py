import os
import subprocess
from helpers.Project import Project
from .project_generator import project_generator


@project_generator(name="flutter",
                   language="Dart, Kotlin, Swift",
                   topics=["Flutter", "mobile", "dart", "kotlin", "swift"])
class Flutter:
    """
    Creates a Next.JS web app using create-next-app.
    See https://docs.flutter.dev/reference/flutter-cli
    """

    def create_new_project(self, project: Project):
        cmd = ["flutter", "create", project.name]

        # if (project.language == "TypeScript"):
        #     cmd.append("--template typescript")

        # Run the command
        os.chdir(os.path.pardir(project.root_path))
        subprocess.run(cmd)
        os.chdir(project.root_path)
