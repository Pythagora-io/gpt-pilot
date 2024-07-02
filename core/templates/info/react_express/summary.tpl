Here's what's already been implemented:

* {{ description }}
* Frontend:
    * ReactJS based frontend in `ui/` folder using Vite devserver
    * Integrated shadcn-ui component library with Tailwind CSS framework
    * Client-side routing using `react-router-dom` with page components defined in `ui/pages/` and other components in `ui/components`
    * Implememented pages:
        * Home - home (index) page (`/`)
        {% if options.auth %}
        * Login - login page (`/login/`) - on login, stores the auth token to `token` variable in local storage
        * Register - register page (`/register/`)
        {% endif %}
* Backend:
    * Express-based server implementing REST API endpoints in `api/`
    {% if options.db_type == "sql" %}
    * Relational (SQL) database support with Prisma ORM using SQLite as the database
    {% elif options.db_type == "nosql" %}
    * MongoDB database support with Mongoose
    {% endif %}
    {% if options.email %}
    * Email sending support using Nodemailer
    {% endif %}
    {% if options.auth %}
    * Token-based authentication (using opaque bearer tokens)
    * User authentication (email + password):
        * login/register API endpoints in `/api/routes/authRoutes.js`
        * authorization middleware in `/api/middlewares/authMiddleware.js`
        * user management logic in `/api/services/userService.js`
    {% endif %}
* Development server:
    * Vite devserver for frontend (`npm run dev:ui` to start the Vite dev server)
    * Nodemon for backend (`npm run dev:api` to start Node.js server with Nodemon)
    * Concurrently to run both servers together with a single command (`npm run dev`) - the preferred way to start the server in development
* Notes:
    {% if options.db_type == "sql" %}
    * Whenever a database model is changed or added in `schema.prisma`, remember to run `npx prisma format && npx prisma generate` to update the Prisma client
    * For model relationships, remember to always also add the reverse relationship in `schema.prisma` at the same time, otherwise the database migration will fail
    {% endif %}
