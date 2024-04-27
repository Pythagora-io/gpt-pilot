from peewee import Model, CharField, TextField, IntegerField, SqliteDatabase

# Connect to an SQLite database
db = SqliteDatabase('project-specs.sqlite')

class ProcessedFile(Model):
    name = CharField()
    path = CharField()
    type = CharField()
    standalone_description = TextField(null=True)
    contextual_description = TextField(null=True)

    class Meta:
        database = db  # This model uses the "files.db" database.

def initialize_db():
    """ Create tables if they do not exist. """
    db.connect()
    db.create_tables([ProcessedFile], safe=True)

def save_processed_file(name, path, type, standalone_description='', contextual_description=''):
    """
    Save or update a processed file's content in the database along with pass number and type.
    """
    query = ProcessedFile.select().where(ProcessedFile.path == path)
    if query.exists():
        # Update the existing record
        (ProcessedFile
         .update(type=type, standalone_description=standalone_description,
                 contextual_description=contextual_description)
         .where(ProcessedFile.name == name)
         .execute())
    else:
        # Create a new record
        ProcessedFile.create(name=name, path=path, type=type, standalone_description=standalone_description,
                             contextual_description=contextual_description)
