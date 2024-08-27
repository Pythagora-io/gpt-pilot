from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.db.models.project_state import TaskStatus
from core.log import get_logger
from core.ui.base import success_source

log = get_logger(__name__)


class TechnicalWriter(BaseAgent):
    agent_type = "tech-writer"
    display_name = "Technical Writer"

    async def run(self) -> AgentResponse:
        n_tasks = len(self.current_state.tasks)
        # current task is still "unfinished" at this point but for purposes of this agent, we want to consider
        # it as "finished" and that is why we are subtracting 1 from the total number of unfinished tasks
        n_unfinished = len(self.current_state.unfinished_tasks) - 1

        if n_unfinished in [n_tasks // 2, 1]:
            # Halfway through the initial project, and at the last task
            await self.send_congratulations()
            await self.create_readme()

        self.next_state.action = "Create README.md"
        self.next_state.set_current_task_status(TaskStatus.DOCUMENTED)
        return AgentResponse.done(self)

    async def send_congratulations(self):
        n_tasks = len(self.current_state.tasks)
        if not n_tasks:
            log.warning("No tasks found in the project")
            return

        n_unfinished = len(self.current_state.unfinished_tasks) - 1
        n_finished = n_tasks - n_unfinished
        pct_finished = int(n_finished / n_tasks * 100)
        n_files = len(self.current_state.files)
        n_lines = sum(len(f.content.content.splitlines()) for f in self.current_state.files)
        await self.ui.send_message(
            "\n\n".join(
                [
                    f"CONGRATULATIONS! You reached {pct_finished}% of your project generation!",
                    f"For now, you have created {n_files} files with a total of {n_lines} lines of code.",
                    "Before continuing, Pythagora will create some documentation for the project...",
                ]
            ),
            source=success_source,
        )

    async def create_readme(self):
        await self.send_message("Creating README ...")

        llm = self.get_llm(stream_output=True)
        convo = AgentConvo(self).template("create_readme")
        llm_response: str = await llm(convo)
        await self.state_manager.save_file("README.md", llm_response)
