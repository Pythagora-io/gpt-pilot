import json
import sys
from copy import deepcopy
from typing import TYPE_CHECKING, Optional

import jsonref
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

    @staticmethod
    def _serialize_prompt_context(context: dict) -> dict:
        """
        Convert data to JSON serializable format

        This is done by replacing non-serializable values with
        their string representations. This is useful for logging.
        """
        return json.loads(json.dumps(context, default=lambda o: str(o)))

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
        self.prompt_log.append(
            {
                "template": f"{self.agent_instance.agent_type}/{template_name}",
                "context": self._serialize_prompt_context(kwargs),
            }
        )
        return self

    def fork(self) -> "AgentConvo":
        child = AgentConvo(self.agent_instance)
        child.messages = deepcopy(self.messages)
        child.prompt_log = deepcopy(self.prompt_log)
        return child

    def trim(self, trim_index: int, trim_count: int) -> "AgentConvo":
        """
        Trim the conversation starting from the given index by 1 message.
        :param trim_index:
        :return:
        """
        self.messages = self.messages[:trim_index] + self.messages[trim_index + trim_count :]
        return self

    def require_schema(self, model: BaseModel) -> "AgentConvo":
        def remove_defs(d):
            if isinstance(d, dict):
                return {k: remove_defs(v) for k, v in d.items() if k != "$defs"}
            elif isinstance(d, list):
                return [remove_defs(v) for v in d]
            else:
                return d

        # We want to make the schema as simple as possible to avoid confusing the LLM,
        # so we remove (dereference) all the refs we can and show the "final" schema version.
        schema_txt = json.dumps(remove_defs(jsonref.loads(json.dumps(model.model_json_schema()))))
        self.user(
            f"IMPORTANT: Your response MUST conform to this JSON schema:\n```\n{schema_txt}\n```."
            f"YOU MUST NEVER add any additional fields to your response, and NEVER add additional preamble like 'Here is your JSON'."
        )
        return self

    def remove_last_x_messages(self, x: int) -> "AgentConvo":
        """
        Remove the last `x` messages from the conversation.
        """
        self.messages = self.messages[:-x]
        return self
