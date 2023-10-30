from base64 import b64decode

from peewee import SqliteDatabase, PostgresqlDatabase
import pytest

from database.config import (
    DATABASE_TYPE,
    DB_NAME,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
)
from database.database import TABLES
from database.models.user import User
from database.models.app import App
from database.models.file_snapshot import FileSnapshot
from database.models.files import File
from database.models.development_steps import DevelopmentSteps

EMPTY_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def database():
    """
    Set up a new empty initialized test database.

    In case of SQlite, the database is created in-memory. In case of PostgreSQL,
    the database should already exist and be empty.

    This fixture will create all the tables and run the test in an isolated transaction.
    which gets rolled back after the test. The fixture also drops all the tables at the
    end.
    """
    if DATABASE_TYPE == "postgres":
        if not DB_NAME:
            raise ValueError(
                "PostgreSQL database name (DB_NAME) environment variable not set"
            )
        db = PostgresqlDatabase(
            DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
        )
    elif DATABASE_TYPE == "sqlite":
        db = SqliteDatabase(":memory:")
    else:
        raise ValueError(f"Unexpected database type: {DATABASE_TYPE}")

    db.bind(TABLES)

    class PostgresRollback(Exception):
        """
        Mock exception to ensure rollback after each test.

        Even though we drop the tables at the end of each test, if the test
        fails due to database integrity error, we have to roll back the
        transaction otherwise PostgreSQL will refuse any further work.

        The easiest and safest is to always roll back the transaction.
        """

        pass

    with db:
        try:
            db.create_tables(TABLES)
            with db.atomic():
                yield db
                raise PostgresRollback()
        except PostgresRollback:
            pass
        finally:
            db.drop_tables(TABLES)


def test_create_tables(database):
    """
    Test that database tables are created for all the models.
    """
    from database.database import TABLES

    with database:
        tables = database.get_tables()
        expected_tables = [table._meta.table_name for table in TABLES]
        assert set(tables) == set(expected_tables)


@pytest.mark.parametrize(
    ("content", "expected_content"),
    [
        ("ascii text", "ascii text"),
        ("non-ascii text: ščćž", "non-ascii text: ščćž"),
        ("with null byte \0", "with null byte \0"),
        (EMPTY_PNG, EMPTY_PNG),
    ],
)
def test_file_snapshot(content, expected_content):
    user = User.create(email="", password="")
    app = App.create(user=user)
    step = DevelopmentSteps.create(app=app, llm_response={})
    file = File.create(app=app, name="test", path="test", full_path="test")

    fs = FileSnapshot.create(
        app=app,
        development_step=step,
        file=file,
        content=content,
    )
    from_db = FileSnapshot.get(id=fs.id)
    assert from_db.content == expected_content
