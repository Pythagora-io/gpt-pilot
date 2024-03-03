import os
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from utils.style import color_green_bold
from logger.logger import logger
from utils.exit import trace_code_event

from .node_express_mongoose import NODE_EXPRESS_MONGOOSE
from .render import Renderer

if TYPE_CHECKING:  # noqa
    from helpers.Project import Project  # noqa

PROJECT_TEMPLATES = {
    "node_express_mongoose": NODE_EXPRESS_MONGOOSE,
}


def apply_project_template(
    project: "Project",
) -> Optional[str]:
    """
    Apply a project template to a new project.

    :param project: the project object
    :return: a summary of the applied template, or None if no template was applied

    If project.project_template is None (not selected), or not one of the supported
    templates, do nothing.

    Note: the template summary is injected in the project description, and the
    created files are saved to a snapshot of the last development step (LLM request).
    """
    template_name = project.project_template
    if not template_name or template_name not in PROJECT_TEMPLATES:
        logger.warning(f"Project template '{template_name}' not found, ignoring")
        return None

    root_path = project.root_path
    project_name = project.args['name']
    project_description = project.main_prompt
    template = PROJECT_TEMPLATES[template_name]
    install_hook = template.get("install_hook")

    r = Renderer(
        os.path.join(os.path.dirname(__file__), "tpl")
    )

    files = r.render_tree(
        template["path"],
        {
            "project_name": project_name,
            "project_description": project_description,
            "random_secret": uuid4().hex,
        },
    )

    project_files = []

    for file_name, file_content in files.items():
        full_path = os.path.join(root_path, file_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        rel_dir = os.path.dirname(file_name)
        project_files.append({
            "name": os.path.basename(file_name),
             # ensure the path is compatible with how the rest of GPT Pilot thinks about paths
            "path": "/" if rel_dir in ["", "."] else rel_dir,
            "content": file_content,
        })

    print(color_green_bold(f"Applying project template {template['description']}...\n"))
    logger.info(f"Applying project template {template_name}...")

    project.save_files_snapshot(project.checkpoints['last_development_step']['id'])

    try:
        if install_hook:
            install_hook(project)
    except Exception as err:
        logger.info(
            f"Error running install hook for project template '{template_name}': {err}",
            exc_info=True,
        )

    trace_code_event('project-template', {'template': template_name})
    summary = "The code so far includes:\n" + template["summary"]
    return summary
