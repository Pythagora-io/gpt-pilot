# database.py

import psycopg2
import json
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from const import db
from logger.logger import logger


def create_connection():
    conn = psycopg2.connect(
        host=db.DB_HOST,
        database=db.DB_NAME,
        port=db.DB_PORT,
        user=db.DB_USER,
        password=db.DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return conn


def create_tables():
    commands = (
        """
        DROP TABLE IF EXISTS progress_steps;
        DROP TABLE IF EXISTS apps;
        DROP TABLE IF EXISTS users;
        """,
        """
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE apps (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            app_id UUID NOT NULL UNIQUE,
            app_type VARCHAR(255) NOT NULL,
            status VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON UPDATE CASCADE ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE progress_steps (
            id SERIAL PRIMARY KEY,
            app_id UUID NOT NULL,
            step VARCHAR(255) NOT NULL,
            data TEXT,
            completed BOOLEAN NOT NULL,
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (app_id)
                REFERENCES apps (app_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            UNIQUE (app_id, step)
        )
        """)

    conn = None
    try:
        conn = create_connection()
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        cur.close()
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


def save_app(user_id, app_id, app_type):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = %s", (str(user_id),))
    if cursor.fetchone() is None:
        # If user doesn't exist, create a new user
        cursor.execute("INSERT INTO users (id, username, email, password) VALUES (%s, 'username', 'email', 'password')",
                       (str(user_id),))

    # Now save or update the app
    cursor.execute("""
        INSERT INTO apps (user_id, app_id, app_type, status)
        VALUES (%s, %s, %s, 'started')
        ON CONFLICT (app_id) DO UPDATE SET
        user_id = EXCLUDED.user_id, app_type = EXCLUDED.app_type, status = EXCLUDED.status
        RETURNING id
    """, (str(user_id), str(app_id), app_type))

    conn.commit()
    cursor.close()
    conn.close()

    logger.info('App saved')

    return


def save_progress(app_id, step, data):
    conn = create_connection()
    cursor = conn.cursor()

    # Check if the data is a dictionary. If it is, convert it to a JSON string.
    if isinstance(data, dict):
        data = json.dumps(data)

    # INSERT the data, but on conflict (if the app_id and step combination already exists) UPDATE the data
    insert = sql.SQL(
        """INSERT INTO progress_steps (app_id, step, data, completed)
           VALUES (%s, %s, %s, false)
           ON CONFLICT (app_id, step) DO UPDATE
           SET data = excluded.data, completed = excluded.completed"""
    )

    cursor.execute(insert, (app_id, step, data))

    conn.commit()
    cursor.close()
    conn.close()


def get_apps_by_id(app_id):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM apps WHERE app_id = %s", (str(app_id),))
    apps = cursor.fetchall()

    cursor.close()
    conn.close()

    return apps


def get_progress_steps(app_id, step=None):
    conn = create_connection()
    cursor = conn.cursor()

    if step:
        cursor.execute("SELECT * FROM progress_steps WHERE app_id = %s AND step = %s", (app_id, step))
    else:
        cursor.execute("SELECT * FROM progress_steps WHERE app_id = %s", (app_id,))
    steps = cursor.fetchall()

    cursor.close()
    conn.close()

    return steps


if __name__ == "__main__":
    create_tables()
