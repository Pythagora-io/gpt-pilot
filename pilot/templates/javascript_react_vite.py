from helpers.cli import execute_command

def install_hook(project):
    """
    Command to run to complete the project scaffolding setup.

    :param project: the project object
    """
    execute_command(project, "npm init vite . --template react && npm install")

JAVASCRIPT_REACT_VITE = {
    "path": "javascript_react_vite",
    "description": "JavaScript with React web app using Vite",
    "summary": "\n".join([
        "* Initial setup with Vite for fast development",
        "* Basic project structure for React development",
        "* Development server setup for hot reloading",
        "* Minimal configuration to get started with React",
        "* You can further customize the project as needed",
    ]),
    "install_hook": install_hook,
}
