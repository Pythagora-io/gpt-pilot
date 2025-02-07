from json import loads
from os.path import dirname, join
from typing import TYPE_CHECKING, Any, Optional, Type
from uuid import uuid4

from pydantic import BaseModel

from core.log import get_logger
from core.templates.render import Renderer

if TYPE_CHECKING:
    from core.proc.process_manager import ProcessManager
    from core.state.state_manager import StateManager

log = get_logger(__name__)


class NoOptions(BaseModel):
    """
    Options class for templates that do not require any options.
    """

    class Config:
        extra = "allow"

    pass


class BaseProjectTemplate:
    """
    Base project template, providing a common interface for all project templates.
    """

    name: str
    path: str
    description: str
    options_class: Type[BaseModel]
    options_description: str
    file_descriptions: dict

    def __init__(
        self,
        options: BaseModel,
        state_manager: "StateManager",
        process_manager: "ProcessManager",
    ):
        """
        Create a new project template.

        :param options: The options to use for the template.
        :param state_manager: The state manager instance to save files to.
        :param process_manager: ProcessManager instance to run the install commands.
        """
        if isinstance(options, dict):
            options = self.options_class(**options)

        self.options = options
        self.state_manager = state_manager
        self.process_manager = process_manager

        self.file_renderer = Renderer(join(dirname(__file__), "tree"))
        self.info_renderer = Renderer(join(dirname(__file__), "info"))

    def filter(self, path: str) -> Optional[str]:
        """
        Filter a file path to be included in the rendered template.

        The method is called for every file in the template tree before rendering.
        If the method returns None or an empty string, the file will be skipped.
        Otherwise, the file will be rendered and stored under the file name
        matching the provided filename.

        By default (base template), this function returns the path as-is.

        :param path: The file path to include or exclude.
        :return: The path to use, or None if the file should be skipped.
        """
        return path

    async def apply(self) -> Optional[str]:
        """
        Apply a project template to a new project.

        :param template_name: The name of the template to apply.
        :param state_manager: The state manager instance to save files to.
        :param process_manager: The process manager instance to run install hooks with.
        :return: A summary of the applied template, or None if no template was applied.
        """
        state = self.state_manager.current_state
        project_name = state.branch.project.name
        project_folder = state.branch.project.folder_name
        project_description = state.specification.description

        log.info(f"Applying project template {self.name} with options: {self.options_dict}")

        files = self.file_renderer.render_tree(
            self.path,
            {
                "project_name": project_name,
                "project_folder": project_folder,
                "project_description": project_description,
                "random_secret": uuid4().hex,
                "options": self.options_dict,
            },
            self.state_manager.file_system.root,
            self.filter,
        )

        for file_name, file_content in files.items():
            desc = self.file_descriptions.get(file_name)
            metadata = {"description": desc} if desc else None
            await self.state_manager.save_file(
                file_name,
                file_content,
                metadata=metadata,
                from_template=True,
            )

        try:
            await self.install_hook()
        except Exception as err:
            log.error(
                f"Error running install hook for project template '{self.name}': {err}",
                exc_info=True,
            )

        return self.info_renderer.render_template(
            join(self.path, "summary.tpl"),
            {
                "description": self.description,
                "options": self.options,
            },
        )

    async def install_hook(self):
        """
        Command to run to complete the project scaffolding setup.
        """
        raise NotImplementedError()

    @property
    def options_dict(self) -> dict[str, Any]:
        """Template options as a Python dictionary."""
        return loads(self.options.model_dump_json())
