import json
import sys
from copy import deepcopy
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from core.config import get_config
from core.llm.convo import Convo
from core.llm.prompt import JinjaFileTemplate
from core.log import get_logger

if TYPE_CHECKING:
    from core.agents.response import BaseAgent

log = get_logger(__name__)


class AgentConvo(Convo):
    prompt_loader: Optional[JinjaFileTemplate] = None

    def __init__(self, agent: "BaseAgent"):
        self.agent_instance = agent
        super().__init__()
        try:
            system_message = self.render("system")
            self.system(system_message)
        except ValueError as err:
            log.warning(f"Agent {agent.__class__.__name__} has no system prompt: {err}")

    @classmethod
    def _init_templates(cls):
        if cls.prompt_loader is not None:
            return

        config = get_config()
        cls.prompt_loader = JinjaFileTemplate(config.prompt.paths)

    def _get_default_template_vars(self) -> dict:
        if sys.platform == "win32":
            os = "Windows"
        elif sys.platform == "darwin":
            os = "macOS"
        else:
            os = "Linux"

        return {
            "state": self.agent_instance.current_state,
            "os": os,
        }

    def render(self, name: str, **kwargs) -> str:
        self._init_templates()

        kwargs.update(self._get_default_template_vars())

        # Jinja uses "/" even in Windows
        template_name = f"{self.agent_instance.agent_type}/{name}.prompt"
        log.debug(f"Loading template {template_name}")
        return self.prompt_loader(template_name, **kwargs)

    def template(self, template_name: str, **kwargs) -> "AgentConvo":
        message = self.render(template_name, **kwargs)
        self.user(message)
        return self

    def fork(self) -> "AgentConvo":
        child = AgentConvo(self.agent_instance)
        child.messages = deepcopy(self.messages)
        return child

    def require_schema(self, model: BaseModel) -> "AgentConvo":
        schema_txt = json.dumps(model.model_json_schema())
        self.user(f"IMPORTANT: Your response MUST conform to this JSON schema:\n```\n{schema_txt}\n```")
        return self
