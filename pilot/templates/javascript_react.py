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
    "files": {
        "vite.config.js": "Configuration file for Vite, a fast developer-friendly Javascript bundler/devserver.",
        "index.html": "Main entry point for the project. It includes a basic HTML structure with a root div element and a script tag importing a JavaScript file named main.jsx using the module type. References: src/main.jsx",
        ".eslintrc.cjs": "Configuration file for ESLint, a static code analysis tool for identifying problematic patterns found in JavaScript code. It defines rules for linting JavaScript code with a focus on React applications.",
        ".gitignore": "Specifies patterns to exclude files and directories from being tracked by Git version control system. It is used to prevent certain files from being committed to the repository.",
        "package.json": "Standard Nodejs package metadata file, specifies dependencies and start scripts. It also specifies that the project is a module.",
        "public/.gitkeep": "Empty file",
        "src/App.css": "Contains styling rules for the root element of the application, setting a maximum width, centering it on the page, adding padding, and aligning text to the center.",
        "src/index.css": "Defines styling rules for the root element, body, and h1 elements of a web page.",
        "src/App.jsx": "Defines a functional component that serves as the root component in the project. The component is exported as the default export. References: src/App.css",
        "src/main.jsx": "Main entry point for a React application. It imports necessary modules, renders the main component 'App' inside a 'React.StrictMode' component, and mounts it to the root element in the HTML document. References: App.jsx, index.css",
        "src/assets/.gitkeep": "Empty file",
    }
}
