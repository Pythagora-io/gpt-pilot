from os.path import isdir
from typing import Any, Optional

from jinja2 import BaseLoader, Environment, FileSystemLoader, StrictUndefined, TemplateNotFound


class FormatTemplate:
    def __call__(self, template: str, **kwargs: dict[str, Any]) -> str:
        return template.format(**kwargs)


class BaseJinjaTemplate:
    def __init__(self, loader: Optional[BaseLoader]):
        self.env = Environment(
            loader=loader,
            autoescape=False,
            lstrip_blocks=True,
            trim_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )


class JinjaStringTemplate(BaseJinjaTemplate):
    def __init__(self):
        super().__init__(None)

    def __call__(self, template: str, **kwargs: dict[str, Any]) -> str:
        tpl = self.env.from_string(template)
        return tpl.render(**kwargs)


class JinjaFileTemplate(BaseJinjaTemplate):
    def __init__(self, template_dirs: list[str]):
        for td in template_dirs:
            if not isdir(td):
                raise ValueError(f"Template directory does not exist: {td}")
        super().__init__(FileSystemLoader(template_dirs))

    def __call__(self, template: str, **kwargs: dict[str, Any]) -> str:
        try:
            tpl = self.env.get_template(template)
        except TemplateNotFound as err:
            raise ValueError(f"Template not found: {template}") from err
        return tpl.render(**kwargs)


__all__ = ["FormatTemplate", "JinjaStringTemplate", "JinjaFileTemplate"]
