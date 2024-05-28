from typing import Optional

from core.agents.convo import AgentConvo


class IterationPromptMixin:
    """
    Provides a method to find a solution to a problem based on user feedback.

    Used by ProblemSolver and Troubleshooter agents.
    """

    async def find_solution(
        self,
        user_feedback: str,
        *,
        user_feedback_qa: Optional[list[str]] = None,
        next_solution_to_try: Optional[str] = None,
    ) -> str:
        """
        Generate a new solution for the problem the user reported.

        :param user_feedback: User feedback about the problem.
        :param user_feedback_qa: Additional q/a about the problem provided by the user (optional).
        :param next_solution_to_try: Hint from ProblemSolver on which solution to try (optional).
        :return: The generated solution to the problem.
        """
        llm = self.get_llm()
        convo = AgentConvo(self).template(
            "iteration",
            current_task=self.current_state.current_task,
            user_feedback=user_feedback,
            user_feedback_qa=user_feedback_qa,
            next_solution_to_try=next_solution_to_try,
        )
        llm_solution: str = await llm(convo)
        return llm_solution
