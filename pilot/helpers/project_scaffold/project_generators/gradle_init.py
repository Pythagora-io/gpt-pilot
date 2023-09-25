import os
import subprocess
from .project_generator import project_generator


@project_generator(name='Gradle Init',
                   language='Java, Kotlin, Groovy, Swift, C++',
                   topics=['gradle', 'java', 'kotlin', 'groovy', 'swift', 'c++'])
class GradleInit:
    """
    Generates a new Gradle build using the `gradle init` command.
    Can be used to generate a Java, Kotlin, Groovy, Scala, Swift, or C++ project.
    """

    def get_documentation_url(self):
        return 'https://docs.gradle.org/current/userguide/build_init_plugin.html'

    def create_new_project(self, project):
        """
        `gradle help --task :init`
        """
        project_type = 'java-library'  # basic, cpp-application, cpp-library, groovy-application, groovy-gradle-plugin,
                                    # groovy-library, java-application, java-gradle-plugin, java-library,
                                    # kotlin-application, kotlin-gradle-plugin, kotlin-library,
                                    # pom, scala-library, swift-application, swift-library
        dsl = 'kotlin'  # or 'groovy'
        test_framework = 'junit-jupiter'  # junit, junit-jupiter, kotlintest, scalatest, spock, testng
        package = 'com.example'

        cmd = [
            'gradle', 'init',
            '--project_name', project.name,
            '--package', package,
            '--type', project_type,
            '--dsl', dsl,
            '--test-framework', test_framework,
        ]

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
