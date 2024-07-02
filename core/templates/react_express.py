from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from core.log import get_logger

from .base import BaseProjectTemplate

log = get_logger(__name__)


class DatabaseType(str, Enum):
    SQL = "sql"
    NOSQL = "nosql"
    NONE = "none"


class TemplateOptions(BaseModel):
    db_type: DatabaseType = Field(
        DatabaseType.NONE,
        description="Type of database to use in the project: relational/SQL (eg SQLite or Postgres), nosql (eg Mongo or Redis) or no database at all",
    )
    auth: bool = Field(
        description="Whether the app supports users and email/password authentication",
    )


TEMPLATE_OPTIONS = """
* Database Type (`db_type`): What type of database should the project use: SQL (relational database like SQLite or Postgres), NoSQL (MongoDB, Redis), or no database at all.
* Authentication (`auth`): Does the project support users registering and authenticating (using email/password).
"""


class ReactExpressProjectTemplate(BaseProjectTemplate):
    stack = "fullstack"
    name = "react_express"
    path = "react_express"
    description = "React frontend with Node/Express REST API backend"
    file_descriptions = {
        ".babelrc": "Configuration file used by Babel, a JavaScript transpiler, to define presets for transforming code. In this specific file, two presets are defined: 'env' with a target of 'node' set to 'current', and 'jest' for Jest testing framework.",
        ".env": "Contains environment variables used to configure the application. It specifies the Node environment, log level, port to listen on, database provider and URL, as well as the session secret string.",
        ".eslintrc.json": "Contains ESLint configuration settings for the project. It specifies the environment (browser, ES2021, Node.js, Jest), extends the ESLint recommended rules, sets parser options for ECMAScript version 12 and module source type, and defines a custom rule to flag unused variables except for 'req', 'res', and 'next' parameters.",
        ".gitignore": "Specifies patterns to exclude certain files and directories from being tracked by Git version control. It helps in preventing unnecessary files from being committed to the repository.",
        "README.md": "Main README for a time-tracking web app for freelancers. The app uses React for the frontend, Node/Express for the backend, Prisma ORM, and SQLite database. It also utilizes Bootstrap for UI styling. The app allows users to register with email and password, uses opaque bearer tokens for authentication, and provides features like time tracking, saving time entries, viewing recent entries, generating reports, and exporting time entries in CSV format. The README also includes instructions for installation, development, testing, production deployment, and Docker usage.",
        "api/app.js": "Sets up an Express app for handling API routes and serving a pre-built frontend. It enables CORS, parses JSON and URL-encoded data, serves static files, and defines routes for authentication and API endpoints. Additionally, it serves the pre-built frontend from the '../dist' folder for all other routes.",
        "api/middlewares/authMiddleware.js": "Implements middleware functions for authentication and user authorization. The 'authenticateWithToken' function checks the Authorization header in the request, extracts the token, and authenticates the user using the UserService. The 'requireUser' function ensures that a user is present in the request object before allowing access to subsequent routes.",
        "api/middlewares/errorMiddleware.js": "Implements middleware functions for handling 404 and 500 errors in an Express API. The 'handle404' function is responsible for returning a 404 response when a requested resource is not found or an unsupported HTTP method is used. The 'handleError' function is used to handle errors that occur within route handlers by logging the error details and sending a 500 response.",
        "api/models/init.js": "Initializes the database client for interacting with the database.",
        "api/models/user.js": "Defines a Mongoose schema for a user in a database, including fields like email, password, token, name, creation date, last login date, and account status. It also includes methods for authenticating users with password or token, setting and regenerating passwords, and custom JSON transformation. The file exports a Mongoose model named 'User' based on the defined schema.",
        "api/routes/authRoutes.js": "Defines routes related to user authentication using Express.js. It includes endpoints for user login, registration, logout, and password management. The file imports services, middlewares, and utilities required for handling authentication logic.",
        "api/routes/index.js": "Defines the API routes using the Express framework. It creates an instance of the Express Router and exports it to be used in the main application. The routes defined in this file are expected to have a '/api/' prefix to differentiate them from UI/frontend routes.",
        "api/services/userService.js": "Implements a UserService class that provides various methods for interacting with user data in the database. It includes functions for listing users, getting a user by ID or email, updating user information, deleting users, authenticating users with password or token, creating new users, setting user passwords, and regenerating user tokens. The class utilizes the 'crypto' library for generating random UUIDs and imports functions from 'password.js' for password hashing and validation.",
        "api/utils/log.js": "Defines a logger utility using the 'pino' library for logging purposes. It sets the log level based on the environment variable 'LOG_LEVEL' or defaults to 'info' in production and 'debug' in other environments. It validates the provided log level against the available levels in 'pino' and throws an error if an invalid level is specified. The logger function creates a new logger instance with the specified name and log level.",
        "api/utils/mail.js": "Implements a utility function to send emails using nodemailer. It reads configuration options from environment variables and creates a nodemailer transporter with the specified options. The main function exported from this file is used to send emails by passing the necessary parameters like 'from', 'to', 'subject', and 'text'.",
        "api/utils/password.js": "Implements functions related to password hashing and validation using the bcrypt algorithm. It provides functions to generate a password hash, validate a password against a hash, and check the format of a hash.",
        "index.html": "The main entry point for the web application front-end. It defines the basic structure of an HTML document with a title and a root div element where the application content will be rendered. Additionally, it includes a script tag that imports the main.jsx file as a module, indicating that this file contains JavaScript code to be executed in a modular fashion.",
        "package.json": "Configuration file used for both Node.js/Express backend and React/Vite frontend define metadata about the project such as name, version, description, dependencies, devDependencies, scripts, etc. It also specifies the entry point of the application through the 'main' field.",
        "prisma/schema.prisma": "Defines the Prisma ORM schema for the project. It specifies the data source configuration, generator settings, and a 'User' model with various fields like id, email, password, token, name, createdAt, lastLoginAt, and isActive. It also includes index definitions for 'email' and 'token' fields.",
        "public/.gitkeep": "(empty file)",
        "server.js": "The main entry point for the backend. It sets up an HTTP server using Node.js's 'http' module, loads environment variables using 'dotenv', imports the main application logic from 'app.js', and initializes a logger from 'log.js'. It also handles uncaught exceptions and unhandled rejections, logging errors and closing the server accordingly. The main function starts the server on a specified port, defaulting to 3000 if not provided in the environment variables.",
        "ui/assets/.gitkeep": "(empty file)",
        "ui/index.css": "Defines main styling rules for the user interface elements. It sets the root font properties, body layout, and heading styles.",
        "ui/main.jsx": "Responsible for setting up the main UI components of the application using React and React Router. It imports necessary dependencies like React, ReactDOM, and react-router-dom. It also imports the main CSS file for styling. The file defines the main router configuration for the app, setting up the Home page to be displayed at the root path. Finally, it renders the main UI components using ReactDOM.createRoot.",
        "ui/pages/Home.css": "Defines the styling for the home page of the UI. It sets the maximum width of the root element to 1280px, centers it horizontally on the page, adds padding around it, and aligns the text in the center.",
        "ui/pages/Home.jsx": "Defines a functional component named 'Home' that gets displayed on the app home page (`/`). It imports styles from the 'Home.css' file.",
        "vite.config.js": "The 'vite.config.js' file is used to configure the Vite build tool for a project. In this specific file, the configuration is defined using the 'defineConfig' function provided by Vite. It includes the 'react' plugin from '@vitejs/plugin-react' to enable React support in the project. The configuration sets up the plugins array with the 'react' plugin initialized.",
    }

    summary = "\n".join(
        [
            "* React-based frontend using Vite devserver",
            "* Radix/Shadcn UI components with Tailwind CSS, and React Router",
            "* Node.js/Express REST API backend",
            "* Dotenv-based configuration",
            "* Database integration - optional (MongoDB via Mongoose or SQL/relational via Prisma)",
            "* User authentication (email+password) - optional",
        ]
    )

    options_class = TemplateOptions
    options_description = TEMPLATE_OPTIONS.strip()

    async def install_hook(self):
        await self.process_manager.run_command("npm install")
        if self.options.db_type == DatabaseType.SQL:
            await self.process_manager.run_command("npx prisma generate")
            await self.process_manager.run_command("npx prisma migrate dev --name initial")

    def filter(self, path: str) -> Optional[str]:
        if not self.options.auth and path in [
            "api/middlewares/authMiddleware.js",
            "api/models/user.js",
            "api/routes/authRoutes.js",
            "api/services/userService.js",
            "api/utils/password.js",
            "ui/pages/Login.jsx",
            "ui/pages/Register.jsx",
        ]:
            log.debug(f"Skipping {path} as auth is disabled")
            return None

        if self.options.db_type != DatabaseType.SQL.value and path in [
            "prisma/schema.prisma",
        ]:
            log.debug(f"Skipping {path} as ORM is not Prisma")
            return None

        if self.options.db_type != DatabaseType.NOSQL.value and path in [
            "api/models/user.js",
        ]:
            log.debug(f"Skipping {path} as Orm is not Mongoose")
            return None

        if self.options.db_type == DatabaseType.NONE.value and path in [
            "api/models/init.js",
        ]:
            log.debug(f"Skipping {path} as database integration is not enabled")
            return None

        log.debug(f"Including project template file {path}")
        return path
