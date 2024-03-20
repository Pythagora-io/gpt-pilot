from helpers.cli import execute_command


def install_hook(project):
    """
    Command to run to complete the project scaffolding setup.

    :param project: the project object
    """
    execute_command(project, "npm install")


JAVASCRIPT_REACT = {
    "path": "javascript_react",
    "description": "React web app using Vite devserver/bundler",
    "summary": "\n".join([
        "* Initial setup with Vite for fast development",
        "* Basic project structure for React development",
        "* Development server setup for hot reloading",
        "* Minimal configuration to get started with React",
    ]),
    "install_hook": install_hook,
}
