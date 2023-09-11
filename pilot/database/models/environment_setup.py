from database.models.components.progress_step import ProgressStep


class EnvironmentSetup(ProgressStep):
    class Meta:
        db_table = 'environment_setup'
