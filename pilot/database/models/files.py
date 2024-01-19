from pathlib import Path
from os.path import commonprefix, join, sep
from peewee import AutoField, CharField, TextField, ForeignKeyField

from database.models.components.base_models import BaseModel
from database.models.app import App


class File(BaseModel):
    id = AutoField()
    app = ForeignKeyField(App, on_delete='CASCADE')
    name = CharField()
    path = CharField()
    full_path = CharField()
    description = TextField(null=True)

    class Meta:
        indexes = (
            (('app', 'name', 'path'), True),
        )

    @staticmethod
    def update_paths():
        workspace_dir = Path(__file__).parent.parent.parent.parent / "workspace"
        if not workspace_dir.exists():
            # This should only happen on first run
            return

        paths = [file.full_path for file in File.select(File.full_path).distinct()]
        if not paths:
            # No paths in the database, so nothing to fix
            return

        common_prefix = commonprefix(paths)
        if commonprefix([common_prefix, str(workspace_dir)]) == str(workspace_dir):
            # Paths are up to date, nothing to fix
            return

        common_sep = "\\" if ":\\" in common_prefix else "/"
        common_parts = common_prefix.split(common_sep)
        try:
            workspace_index = common_parts.index("workspace")
        except ValueError:
            # There's something strange going on, better not touch anything
            return
        old_prefix = common_sep.join(common_parts[:workspace_index + 1])

        print(f"Updating file paths from {old_prefix} to {workspace_dir}")
        for file in File.select().where(File.full_path.startswith(old_prefix)):
            parts = file.full_path.split(common_sep)
            new_path = str(workspace_dir) + sep + sep.join(parts[workspace_index + 1:])
            file.full_path = new_path
            file.save()
