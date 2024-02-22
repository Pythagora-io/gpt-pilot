from helpers.cli import execute_command


def install_hook(project):
    """
    Command to run to complete the project scaffolding setup.

    :param project: the project object
    """
    execute_command(project, "npm install")


NODE_EXPRESS_MONGOOSE = {
    "path": "node_express_mongoose",
    "description": "Node + Express + MongoDB web app with session-based authentication, EJS views and Bootstrap 5",
    "summary": "\n".join([
        "* initial Node + Express setup",
        "* User model in Mongoose ORM with username and password fields, ensuring username is unique and hashing passwords with bcrypt prior to saving to the database",
        "* session-based authentication using username + password (hashed using bcrypt) in routes/authRoutes.js, using express-session",
        "* authentication middleware to protect routes that require login",
        "* EJS view engine, html head, header and footer EJS partials, with included Boostrap 5.x CSS and JS",
        "* routes and EJS views for login, register, and home (main) page",
        "* config loading from environment using dotenv with a placeholder .env.example file: you will need to create a .env file with your own values",
    ]),
    "install_hook": install_hook,
}
