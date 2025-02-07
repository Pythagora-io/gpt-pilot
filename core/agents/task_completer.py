from core.agents.base import BaseAgent
from core.agents.git import GitMixin
from core.agents.response import AgentResponse
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)


class TaskCompleter(BaseAgent, GitMixin):
    agent_type = "pythagora"
    display_name = "Pythagora"

    async def run(self) -> AgentResponse:
        if self.state_manager.git_available and self.state_manager.git_used:
            await self.git_commit()

        current_task_index1 = self.current_state.tasks.index(self.current_state.current_task) + 1
        self.next_state.action = f"Task #{current_task_index1} complete"
        self.next_state.complete_task()
        await self.state_manager.log_task_completed()
        tasks = self.current_state.tasks
        source = self.current_state.current_epic.get("source", "app")
        await self.ui.send_task_progress(
            current_task_index1,
            len(tasks),
            self.current_state.current_task["description"],
            source,
            "done",
            self.current_state.get_source_index(source),
            tasks,
        )
        await telemetry.trace_code_event(
            "task-end",
            {
                "task_index": current_task_index1,
                "num_tasks": len(self.current_state.tasks),
                "num_epics": len(self.current_state.epics),
                "num_iterations": len(self.current_state.iterations),
            },
        )

        if current_task_index1 == len(tasks):
            if source == "app":
                await self.ui.send_app_finished(
                    app_id=str(self.state_manager.project.id),
                    app_name=self.state_manager.project.name,
                    folder_name=self.state_manager.project.folder_name,
                )
            elif source == "feature":
                await self.ui.send_feature_finished(
                    app_id=str(self.state_manager.project.id),
                    app_name=self.state_manager.project.name,
                    folder_name=self.state_manager.project.folder_name,
                )

        return AgentResponse.done(self)
