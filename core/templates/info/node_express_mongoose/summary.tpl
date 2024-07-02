Here's what's already been implemented:

* Node + Express + MongoDB web app with session-based authentication, EJS views and Bootstrap 5
* initial Node + Express setup
* User model in Mongoose ORM with username and password fields, ensuring username is unique and hashing passwords with bcrypt prior to saving to the database
* session-based authentication using username + password (hashed using bcrypt) in routes/authRoutes.js, using express-session
* authentication middleware to protect routes that require login
* EJS view engine, html head, header and footer EJS partials, with included Boostrap 5.x CSS and JS
* routes and EJS views for login, register, and home (main) page
* config loading from environment using dotenv with a placeholder .env.example file: you will need to create a .env file with your own values
