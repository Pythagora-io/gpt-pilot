from helpers.cli import execute_command

def install_hook(project):
    """
    Command to run to complete the project scaffolding setup.

    :param project: the project object
    """
    execute_command(project, "npx create-react-app .")

JAVASCRIPT_REACT = {
    "path": "javascript_react",
    "description": "JavaScript with React web app using create-react-app",
    "summary": "\n".join([
        "* Initial setup with create-react-app",
        "* Basic project structure for React development",
        "* Development server setup for hot reloading",
        "* Minimal configuration to get started with React",
        "* You can further customize the project as needed",
    ]),
    "install_hook": install_hook,
}
