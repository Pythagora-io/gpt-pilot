from core.agents.base import BaseAgent
from core.agents.response import AgentResponse


class LegacyHandler(BaseAgent):
    agent_type = "legacy-handler"
    display_name = "Legacy Handler"

    async def run(self) -> AgentResponse:
        if self.data["type"] == "review_task":
            self.next_state.complete_step("review_task")
            return AgentResponse.done(self)

        raise ValueError(f"Unknown reason for calling Legacy Handler with data: {self.data}")
