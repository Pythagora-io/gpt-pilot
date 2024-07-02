from .base import BaseProjectTemplate, NoOptions


class NodeExpressMongooseProjectTemplate(BaseProjectTemplate):
    stack = "backend"
    name = "node_express_mongoose"
    path = "node_express_mongoose"
    description = "Node + Express + MongoDB web app with session-based authentication, EJS views and Bootstrap 5"
    file_descriptions = {
        ".env.example": "The .env.example file serves as a template for setting up environment variables used in the application. It provides placeholders for values such as the port number, MongoDB database URL, and session secret string.",
        ".env": "This file is a configuration file in the form of a .env file. It contains environment variables used by the application, such as the port to listen on, the MongoDB database URL, and the session secret string.",
        "server.js": "This `server.js` file sets up an Express server with MongoDB database connection, session management using connect-mongo, templating engine EJS, static file serving, authentication routes, error handling, and request logging. [References: dotenv, mongoose, express, express-session, connect-mongo, ./routes/authRoutes]",
        "package.json": "This `package.json` file is used to define the metadata and dependencies for a Node.js project named 'tt0'. It specifies the project name, version, main entry point file, scripts for starting and testing the project, dependencies required by the project, and other metadata like author and license. [References: server.js]",
        "views/login.ejs": "This file represents the login page of a web application using EJS (Embedded JavaScript) templating. It includes partials for the head, header, and footer sections, and contains a form for users to input their username and password to log in. [References: partials/_head.ejs, partials/_header.ejs, partials/_footer.ejs]",
        "views/register.ejs": "The 'views/register.ejs' file contains the HTML markup for a registration form. It includes fields for username and password, along with a button to submit the form and a link to redirect to the login page if the user already has an account. [References: partials/_head.ejs, partials/_header.ejs, partials/_footer.ejs]",
        "views/index.ejs": "This file represents the main view for a web application. It includes partials for the head, header, and footer sections, and contains a simple HTML structure with a main container displaying a heading. [References: partials/_head.ejs, partials/_header.ejs, partials/_footer.ejs, js/main.js]",
        "views/partials/_header.ejs": "This file represents a partial view for the header section of a web page. It includes a navigation bar with a brand logo, toggle button, and links for Home, Login, and Logout based on the user's session status.",
        "views/partials/_head.ejs": "This file represents the partial for the head section of an HTML document. It includes meta tags, a title tag, and links to external CSS files (Bootstrap and a custom stylesheet).",
        "views/partials/_footer.ejs": "This file defines the footer section of a web page using EJS (Embedded JavaScript) templating. It includes a copyright notice and a link to the Bootstrap JavaScript library. [References: https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.min.js]",
        "routes/authRoutes.js": "This file defines routes for user authentication including registration, login, and logout. It interacts with a User model to handle user data and uses bcrypt for password hashing and comparison. [References: models/User.js]",
        "routes/middleware/authMiddleware.js": "This file defines a middleware function called isAuthenticated, which checks if a user is authenticated based on the presence of a userId in the session object. If authenticated, it allows the request to proceed to the next middleware or route handler; otherwise, it returns a 401 status response indicating the user is not authenticated.",
        "models/User.js": "This file defines a Mongoose model for a user with fields for username and password. It includes a pre-save hook to hash the user's password before saving it to the database using bcrypt. [References: mongoose, bcrypt]",
        "public/js/main.js": "The main.js file is a placeholder for future JavaScript code. It currently does not contain any specific functionality.",
        "public/css/style.css": "This file is a placeholder for custom styles. It does not contain any specific styles but is intended for adding custom CSS styles.",
    }
    summary = "\n".join(
        [
            "* initial Node + Express setup",
            "* User model in Mongoose ORM with username and password fields, ensuring username is unique and hashing passwords with bcrypt prior to saving to the database",
            "* session-based authentication using username + password (hashed using bcrypt) in routes/authRoutes.js, using express-session",
            "* authentication middleware to protect routes that require login",
            "* EJS view engine, html head, header and footer EJS partials, with included Boostrap 5.x CSS and JS",
            "* routes and EJS views for login, register, and home (main) page",
            "* config loading from environment using dotenv with a placeholder .env.example file: you will need to create a .env file with your own values",
        ]
    )
    options_class = NoOptions
    options_description = ""

    async def install_hook(self):
        await self.process_manager.run_command("npm install")
