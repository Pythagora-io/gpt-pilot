from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.log import get_logger

log = get_logger(__name__)


class TechnicalWriter(BaseAgent):
    agent_type = "tech-writer"
    display_name = "Technical Writer"

    async def run(self) -> AgentResponse:
        n_tasks = len(self.current_state.tasks)
        n_unfinished = len(self.current_state.unfinished_tasks)

        if n_unfinished in [n_tasks // 2, 1]:
            # Halfway through the initial project, and and at the last task
            await self.create_readme()

        self.next_state.complete_step()
        return AgentResponse.done(self)

    async def create_readme(self):
        await self.ui.send_message("Creating README ...")

        llm = self.get_llm()
        convo = AgentConvo(self).template("create_readme")
        llm_response: str = await llm(convo)
        await self.state_manager.save_file("README.md", llm_response)
