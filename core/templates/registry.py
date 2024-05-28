import os
from enum import Enum
from typing import Optional
from uuid import uuid4

from core.log import get_logger
from core.proc.process_manager import ProcessManager
from core.state.state_manager import StateManager

from .javascript_react import JAVASCRIPT_REACT
from .node_express_mongoose import NODE_EXPRESS_MONGOOSE
from .render import Renderer

PROJECT_TEMPLATES = {
    "node_express_mongoose": NODE_EXPRESS_MONGOOSE,
    "javascript_react": JAVASCRIPT_REACT,
}

log = get_logger(__name__)


class ProjectTemplateEnum(str, Enum):
    """Choices of available project templates."""

    NODE_EXPRESS_MONGOOSE = "node_express_mongoose"
    JAVASCRIPT_REACT = "javascript_react"


async def apply_project_template(
    template_name: str,
    state_manager: StateManager,
    process_manager: ProcessManager,
) -> Optional[str]:
    """
    Apply a project template to a new project.

    :param template_name: The name of the template to apply.
    :param state_manager: The state manager instance to save files to.
    :param process_manager: The process manager instance to run install hooks with.
    :return: A summary of the applied template, or None if no template was applied.
    """
    if not template_name or template_name not in PROJECT_TEMPLATES:
        log.warning(f"Project template '{template_name}' not found, ignoring")
        return None

    project_name = state_manager.current_state.branch.project.name
    project_description = state_manager.current_state.specification.description
    template = PROJECT_TEMPLATES[template_name]
    install_hook = template.get("install_hook")

    # TODO: this could be configurable to get premium templates
    r = Renderer(os.path.join(os.path.dirname(__file__), "tpl"))

    log.info(f"Applying project template {template_name}...")

    files = r.render_tree(
        template["path"],
        {
            "project_name": project_name,
            "project_description": project_description,
            "random_secret": uuid4().hex,
        },
    )

    descriptions = template.get("files", {})
    for file_name, file_content in files.items():
        desc = descriptions.get(file_name)
        metadata = {"description": desc} if desc else None
        await state_manager.save_file(file_name, file_content, metadata=metadata, from_template=True)

    try:
        if install_hook:
            await install_hook(process_manager)
    except Exception as err:
        log.error(
            f"Error running install hook for project template '{template_name}': {err}",
            exc_info=True,
        )

    return template["summary"]


def get_template_summary(template_name: str) -> Optional[str]:
    """
    Get a summary of a project template.

    :param template_name: The name of the project template.
    :return: A summary of the template, or None if no template was found.
    """
    if not template_name or template_name not in PROJECT_TEMPLATES:
        log.warning(f"Project template '{template_name}' not found, ignoring")
        return None
    template = PROJECT_TEMPLATES[template_name]
    return template["summary"]


def get_template_description(template_name: str) -> Optional[str]:
    """
    Get the description of a project template.

    :param template_name: The name of the project template.
    :return: A summary of the template, or None if no template was found.
    """
    if not template_name or template_name not in PROJECT_TEMPLATES:
        log.warning(f"Project template '{template_name}' not found, ignoring")
        return None
    template = PROJECT_TEMPLATES[template_name]
    return template["description"]
