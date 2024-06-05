from core.agents.base import BaseAgent
from core.agents.response import AgentResponse
from core.log import get_logger

log = get_logger(__name__)


class TaskCompleter(BaseAgent):
    agent_type = "pythagora"
    display_name = "Pythagora"

    async def run(self) -> AgentResponse:
        current_task_index1 = self.current_state.tasks.index(self.current_state.current_task) + 1
        self.next_state.action = f"Task #{current_task_index1} complete"
        self.next_state.complete_task()
        await self.state_manager.log_task_completed()
        tasks = self.current_state.tasks
        source = self.current_state.current_epic.get("source", "app")
        await self.ui.send_task_progress(
            tasks.index(self.current_state.current_task) + 1,
            len(tasks),
            self.current_state.current_task["description"],
            source,
            "done",
            self.current_state.get_source_index(source),
            tasks,
        )

        return AgentResponse.done(self)
