# {{ project_name }}

{{ project_description }}

## Quickstart

1. Install required packages:

   ```
   npm install
   ```

2. Update `.env` with your settings.

{% if options.db_type == 'sql' %}
3. Create initial database migration:

   ```
   npx prisma migrate dev --name initial
   ```

    When run the first time, it will also install
    `@prisma/client` and generate client code.

4. Run the tests:
{% else %}
3. Run the tests:
{% endif %}

   ```
   npm run test
   ```

## Development

To run the server in development mode, with log pretty-printing and hot-reload:

```
npm run dev
```

To run the tests, run the `test` script (`npm run test`). ESLint is used for linting and its configuration is specified in `.eslintrc.json`.

Code style is automatically formatted using `prettier`. To manually run prettier, use `npm run prettier`. Better yet, integrate your editor to run it on save.

## Production

To run the app in production, run:

```
npm start
```

Logs will be sent to the standard output in JSON format.
{% if options.bg_tasks %}

## Background tasks with Bull

A simple task queue is built using `bull` and backed by Redis. Tasks are defined and exported in `src/tasks.js`. Call proxies are created automatically and tasks can be queued with:

```
import { tasks } from "./src/utils/queue.js";
const result = await tasks.someFunction(...);
```

To run the worker(s) that will execute the queued tasks, run:

```
npm run worker
```
{% endif %}

## Using Docker

Build the docker image with:

        docker build -t {{ project_folder }} .

The default command is to start the web server (gunicorn). Run the image with `-P` docker option to expose the internal port (3000) and check the exposed port with `docker ps`:

        docker run --env-file .env --P {{ project_folder }}
        docker ps

Make sure you provide the correct path to the env file (this example assumes it's located in the local directory).

To run a custom command using the image (for example, starting the Node
shell):

        docker run --env-file .env {{ project_folder }} npm run shell

For more information on the docker build process, see the included
`Dockerfile`.
