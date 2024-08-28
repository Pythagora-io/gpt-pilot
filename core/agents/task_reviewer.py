from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.log import get_logger

log = get_logger(__name__)


class TaskReviewer(BaseAgent):
    agent_type = "task-reviewer"
    display_name = "Task Reviewer"

    async def run(self) -> AgentResponse:
        response = await self.review_code_changes()
        self.next_state.complete_step()
        return response

    async def review_code_changes(self) -> AgentResponse:
        """
        Review all the code changes during current task.
        """

        log.debug(f"Reviewing code changes for task {self.current_state.current_task['description']}")
        all_feedbacks = [
            iteration["user_feedback"].replace("```", "").strip()
            for iteration in self.current_state.iterations
            # Some iterations are created by the task reviewer and have no user feedback
            if iteration["user_feedback"]
        ]
        bug_hunter_instructions = [
            iteration["bug_hunting_cycles"][-1]["human_readable_instructions"].replace("```", "").strip()
            for iteration in self.current_state.iterations
            if iteration["bug_hunting_cycles"]
        ]

        files_before_modification = self.current_state.modified_files
        files_after_modification = [
            (file.path, file.content.content)
            for file in self.current_state.files
            if (file.path in files_before_modification)
        ]

        llm = self.get_llm()
        # TODO instead of sending files before and after maybe add nice way to show diff for multiple files
        convo = AgentConvo(self).template(
            "review_task",
            all_feedbacks=all_feedbacks,
            files_before_modification=files_before_modification,
            files_after_modification=files_after_modification,
            bug_hunter_instructions=bug_hunter_instructions,
        )
        llm_response: str = await llm(convo, temperature=0.7)

        if "done" in llm_response.strip().lower()[-20:]:
            return AgentResponse.done(self)
        else:
            return AgentResponse.task_review_feedback(self, llm_response)
