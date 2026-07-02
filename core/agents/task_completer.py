from core.agents.base import BaseAgent
from core.agents.git import GitMixin
from core.agents.response import AgentResponse
from core.config.actions import TC_TASK_DONE
from core.log import get_logger
from core.memory import ProjectMemory
from core.telemetry import telemetry

log = get_logger(__name__)


class TaskCompleter(BaseAgent, GitMixin):
    agent_type = "pythagora"
    display_name = "Pythagora"

    async def run(self) -> AgentResponse:
        if self.state_manager.git_available and self.state_manager.git_used:
            await self.git_commit()

        # Capture the task outcome before `complete_task()` advances the pointer, so it
        # can be persisted to project memory (best-effort, no-op when memory is disabled).
        outcome = self._summarize_task_outcome()

        current_task_index1 = self.current_state.tasks.index(self.current_state.current_task) + 1
        self.next_state.action = TC_TASK_DONE.format(current_task_index1)
        self.next_state.complete_task()
        await self._store_task_outcome(outcome)
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

    def _summarize_task_outcome(self) -> str:
        """
        Build a compact, human-readable summary of the finished task and any debugging
        that happened while implementing it. The debugging iterations (problem ->
        solution) are the most valuable thing to remember across sessions.
        """
        task = self.current_state.current_task or {}
        lines = [f"Task: {task.get('description', '').strip()}"]
        for iteration in self.current_state.iterations or []:
            problem = (iteration.get("user_feedback") or "").strip()
            solution = (iteration.get("description") or "").strip()
            if problem or solution:
                lines.append(f"Debugging: {problem or 'issue'} -> {solution or 'resolved'}")
        return "\n".join(lines)

    async def _store_task_outcome(self, outcome: str) -> None:
        """Persist the task outcome to project memory (best-effort; no-op when disabled)."""
        memory = ProjectMemory.for_project(self.state_manager.project.id)
        if memory is None:
            return
        await memory.store(outcome, tags=["gpt-pilot", "task-outcome"])
