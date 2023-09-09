from database.models.components.progress_step import ProgressStep


class EnvironmentSetup(ProgressStep):
    class Meta:
        table_name = 'environment_setup'
