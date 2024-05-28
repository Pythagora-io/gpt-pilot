from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.mixins import IterationPromptMixin
from core.agents.response import AgentResponse
from core.db.models.project_state import TaskStatus
from core.llm.parser import JSONParser, OptionalCodeBlockParser
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)

LOOP_THRESHOLD = 3  # number of iterations in task to be considered a loop


class BugReportQuestions(BaseModel):
    missing_data: list[str] = Field(
        description="Very clear question that needs to be answered to have good bug report."
    )


class Troubleshooter(IterationPromptMixin, BaseAgent):
    agent_type = "troubleshooter"
    display_name = "Troubleshooter"

    async def run(self) -> AgentResponse:
        run_command = await self.get_run_command()

        user_instructions = self.current_state.current_task.get("test_instructions")
        if not user_instructions:
            user_instructions = await self.get_user_instructions()
            if user_instructions is None:
                # LLM decided we don't need to test anything, so we're done with the task
                return await self.complete_task()

            # Save the user instructions for future iterations and rerun
            self.next_state.current_task["test_instructions"] = user_instructions
            self.next_state.flag_tasks_as_modified()
            return AgentResponse.done(self)
        else:
            await self.send_message("Here are instruction on how to test the app:\n\n" + user_instructions)

        # Developer sets iteration as "completed" when it generates the step breakdown, so we can't
        # use "current_iteration" here
        last_iteration = self.current_state.iterations[-1] if self.current_state.iterations else None

        should_iterate, is_loop, user_feedback = await self.get_user_feedback(
            run_command,
            user_instructions,
            last_iteration is not None,
        )
        if not should_iterate:
            # User tested and reported no problems, we're done with the task
            return await self.complete_task()

        user_feedback_qa = await self.generate_bug_report(run_command, user_instructions, user_feedback)

        if is_loop:
            if last_iteration["alternative_solutions"]:
                # If we already have alternative solutions, it means we were already in a loop.
                return self.try_next_alternative_solution(user_feedback, user_feedback_qa)
            else:
                # Newly detected loop, set up an empty new iteration to trigger ProblemSolver
                llm_solution = ""
                await self.trace_loop("loop-feedback")
        else:
            llm_solution = await self.find_solution(user_feedback, user_feedback_qa=user_feedback_qa)

        self.next_state.iterations = self.current_state.iterations + [
            {
                "id": uuid4().hex,
                "user_feedback": user_feedback,
                "user_feedback_qa": user_feedback_qa,
                "description": llm_solution,
                "alternative_solutions": [],
                # FIXME - this is incorrect if this is a new problem; otherwise we could
                # just count the iterations
                "attempts": 1,
                "completed": False,
            }
        ]
        if len(self.next_state.iterations) == LOOP_THRESHOLD:
            await self.trace_loop("loop-start")

        return AgentResponse.done(self)

    async def complete_task(self) -> AgentResponse:
        """
        No more coding or user interaction needed for the current task, mark it as reviewed.
        After this it goes to TechnicalWriter for documentation.
        """
        if len(self.current_state.iterations) >= LOOP_THRESHOLD:
            await self.trace_loop("loop-end")

        current_task_index1 = self.current_state.tasks.index(self.current_state.current_task) + 1
        self.next_state.action = f"Task #{current_task_index1} reviewed"
        self.next_state.set_current_task_status(TaskStatus.REVIEWED)
        return AgentResponse.done(self)

    def _get_task_convo(self) -> AgentConvo:
        # FIXME: Current prompts reuse conversation from the developer so we have to resort to this
        task = self.current_state.current_task
        current_task_index = self.current_state.tasks.index(task)

        return (
            AgentConvo(self)
            .template(
                "breakdown",
                task=task,
                iteration=None,
                current_task_index=current_task_index,
            )
            .assistant(self.current_state.current_task["instructions"])
        )

    async def get_run_command(self) -> Optional[str]:
        if self.current_state.run_command:
            return self.current_state.run_command

        await self.send_message("Figuring out how to run the app ...")

        llm = self.get_llm()
        convo = self._get_task_convo().template("get_run_command")

        # Although the prompt is explicit about not using "```", LLM may still return it
        llm_response: str = await llm(convo, temperature=0, parser=OptionalCodeBlockParser())
        self.next_state.run_command = llm_response
        return llm_response

    async def get_user_instructions(self) -> Optional[str]:
        await self.send_message("Determining how to test the app ...")

        llm = self.get_llm()
        convo = self._get_task_convo().template("define_user_review_goal", task=self.current_state.current_task)
        user_instructions: str = await llm(convo)

        user_instructions = user_instructions.strip()
        if user_instructions.lower() == "done":
            log.debug(f"Nothing to do for user testing for task {self.current_state.current_task['description']}")
            return None

        return user_instructions

    async def get_user_feedback(
        self,
        run_command: str,
        user_instructions: str,
        last_iteration: Optional[dict],
    ) -> tuple[bool, bool, str, str]:
        """
        Ask the user to test the app and provide feedback.

        :return (bool, bool, str): Tuple containing "should_iterate", "is_loop" and
        "user_feedback" respectively.

        If "should_iterate" is False, the user has confirmed that the app works as expected and there's
        nothing for the troubleshooter or problem solver to do.

        If "is_loop" is True, Pythagora is stuck in a loop and needs to consider alternative solutions.

        The last element in the tuple is the user feedback, which may be empty if the user provided no
        feedback (eg. if they just clicked on "Continue" or "I'm stuck in a loop").
        """

        test_message = "Can you check if the app works please?"
        if user_instructions:
            hint = " Here is a description of what should be working:\n\n" + user_instructions

        if run_command:
            await self.ui.send_run_command(run_command)

        buttons = {"continue": "continue"}
        if last_iteration:
            buttons["loop"] = "I'm stuck in a loop"

        user_response = await self.ask_question(test_message, buttons=buttons, default="continue", hint=hint)
        if user_response.button == "continue" or user_response.cancelled:
            return False, False, ""

        if user_response.button == "loop":
            return True, True, ""

        return True, False, user_response.text

    def try_next_alternative_solution(self, user_feedback: str, user_feedback_qa: list[str]) -> AgentResponse:
        """
        Call the ProblemSolver to try an alternative solution.

        Stores the user feedback and sets iteration state (not completed, no description)
        so that ProblemSolver will be triggered.

        :param user_feedback: User feedback to store in the iteration state.
        :param user_feedback_qa: Additional questions/answers about the problem.
        :return: Agent response done.
        """
        next_state_iteration = self.next_state.iterations[-1]
        next_state_iteration["description"] = ""
        next_state_iteration["user_feedback"] = user_feedback
        next_state_iteration["user_feedback_qa"] = user_feedback_qa
        next_state_iteration["attempts"] += 1
        next_state_iteration["completed"] = False
        self.next_state.flag_iterations_as_modified()
        self.next_state.action = f"Alternative solution (attempt #{next_state_iteration['attempts']})"
        return AgentResponse.done(self)

    async def generate_bug_report(
        self,
        run_command: Optional[str],
        user_instructions: str,
        user_feedback: str,
    ) -> list[str]:
        """
        Generate a bug report from the user feedback.

        :param run_command: The command to run to test the app.
        :param user_instructions: Instructions on how to test the functionality.
        :param user_feedback: The user feedback.
        :return: Additional questions and answers to generate a better bug report.
        """
        additional_qa = []
        llm = self.get_llm()
        convo = (
            AgentConvo(self)
            .template(
                "bug_report",
                user_instructions=user_instructions,
                user_feedback=user_feedback,
                # TODO: revisit if we again want to run this in a loop, where this is useful
                additional_qa=additional_qa,
            )
            .require_schema(BugReportQuestions)
        )
        llm_response: BugReportQuestions = await llm(convo, parser=JSONParser(BugReportQuestions))

        if not llm_response.missing_data:
            return []

        for question in llm_response.missing_data:
            if run_command:
                await self.ui.send_run_command(run_command)
            user_response = await self.ask_question(
                question,
                buttons={
                    "continue": "continue",
                    "skip": "Skip this question",
                    "skip-all": "Skip all questions",
                },
                allow_empty=False,
            )
            if user_response.cancelled or user_response.button == "skip-all":
                break
            elif user_response.button == "skip":
                continue

            additional_qa.append(
                {
                    "question": question,
                    "answer": user_response.text,
                }
            )

        return additional_qa

    async def trace_loop(self, trace_event: str):
        state = self.current_state
        task_with_loop = {
            "task_description": state.current_task["description"],
            "task_number": len([t for t in state.tasks if t["status"] == TaskStatus.DONE]) + 1,
            "steps": len(state.steps),
            "iterations": len(state.iterations),
        }
        await telemetry.trace_loop(trace_event, task_with_loop)
