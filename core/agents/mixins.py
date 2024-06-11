from typing import Optional

from core.agents.convo import AgentConvo
from core.db.models.specification import Specification
from core.telemetry import telemetry


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


class SystemDependencyCheckerMixin:
    """
    Provides a method to check whether the required system dependencies are installed.

    Used by Architect and SpecWriter agents. Assumes the agent has access to UI
    and ProcessManager.
    """

    async def check_system_dependencies(self, spec: Specification):
        """
        Check whether the required system dependencies are installed.

        This also stores the app architecture telemetry data, including the
        information about whether each system dependency is installed.

        :param spec: Project specification.
        """
        deps = spec.system_dependencies
        checked = {}

        for dep in deps:
            status_code, _, _ = await self.process_manager.run_command(dep["test"])
            dep["installed"] = bool(status_code == 0)
            if status_code != 0:
                if dep["required_locally"]:
                    remedy = "Please install it before proceeding with your app."
                else:
                    remedy = "If you would like to use it locally, please install it before proceeding."
                await self.send_message(f"❌ {dep['name']} is not available. {remedy}")
                await self.ask_question(
                    f"Once you have installed {dep['name']}, please press Continue.",
                    buttons={"continue": "Continue"},
                    buttons_only=True,
                    default="continue",
                )
                checked[dep["name"]] = "missing"
            else:
                await self.send_message(f"✅ {dep['name']} is available.")
                checked[dep["name"]] = "present"

        telemetry.set(
            "architecture",
            {
                "description": spec.architecture,
                "system_dependencies": deps,
                "package_dependencies": spec.package_dependencies,
                "checked_system_dependencies": checked,
            },
        )
