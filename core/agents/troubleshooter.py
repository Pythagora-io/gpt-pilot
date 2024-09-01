from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.mixins import IterationPromptMixin, RelevantFilesMixin
from core.agents.response import AgentResponse
from core.config import TROUBLESHOOTER_GET_RUN_COMMAND
from core.db.models.file import File
from core.db.models.project_state import IterationStatus, TaskStatus
from core.llm.parser import JSONParser, OptionalCodeBlockParser
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)

LOOP_THRESHOLD = 3  # number of iterations in task to be considered a loop


class BugReportQuestions(BaseModel):
    missing_data: list[str] = Field(
        description="Very clear question that needs to be answered to have good bug report."
    )


class RouteFilePaths(BaseModel):
    files: list[str] = Field(description="List of paths for files that contain routes")


class Troubleshooter(IterationPromptMixin, RelevantFilesMixin, BaseAgent):
    agent_type = "troubleshooter"
    display_name = "Troubleshooter"

    async def run(self) -> AgentResponse:
        if self.current_state.unfinished_iterations:
            if self.current_state.current_iteration.get("status") == IterationStatus.FIND_SOLUTION:
                return await self.propose_solution()
            else:
                raise ValueError("There is unfinished iteration but it's not in FIND_SOLUTION state.")
        else:
            return await self.create_iteration()

    async def propose_solution(self) -> AgentResponse:
        user_feedback = self.current_state.current_iteration.get("user_feedback")
        user_feedback_qa = self.current_state.current_iteration.get("user_feedback_qa")
        bug_hunting_cycles = self.current_state.current_iteration.get("bug_hunting_cycles")

        llm_solution = await self.find_solution(
            user_feedback, user_feedback_qa=user_feedback_qa, bug_hunting_cycles=bug_hunting_cycles
        )

        self.next_state.current_iteration["description"] = llm_solution
        self.next_state.current_iteration["status"] = IterationStatus.IMPLEMENT_SOLUTION
        self.next_state.flag_iterations_as_modified()

        return AgentResponse.done(self)

    async def create_iteration(self) -> AgentResponse:
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
        last_iteration = self.current_state.iterations[-1] if len(self.current_state.iterations) >= 3 else None

        should_iterate, is_loop, bug_report, change_description = await self.get_user_feedback(
            run_command,
            user_instructions,
            last_iteration is not None,
        )
        if not should_iterate:
            # User tested and reported no problems, we're done with the task
            return await self.complete_task()

        user_feedback = bug_report or change_description
        user_feedback_qa = None  # await self.generate_bug_report(run_command, user_instructions, user_feedback)

        if is_loop:
            if last_iteration["alternative_solutions"]:
                # If we already have alternative solutions, it means we were already in a loop.
                return self.try_next_alternative_solution(user_feedback, user_feedback_qa)
            else:
                # Newly detected loop
                iteration_status = IterationStatus.PROBLEM_SOLVER
                await self.trace_loop("loop-feedback")
        elif bug_report is not None:
            iteration_status = IterationStatus.HUNTING_FOR_BUG
        else:
            # should be - elif change_description is not None: - but to prevent bugs with the extension
            # this might be caused if we show the input field instead of buttons
            await self.get_relevant_files(user_feedback)
            iteration_status = IterationStatus.NEW_FEATURE_REQUESTED

        self.next_state.iterations = self.current_state.iterations + [
            {
                "id": uuid4().hex,
                "user_feedback": user_feedback,
                "user_feedback_qa": user_feedback_qa,
                "description": None,
                "alternative_solutions": [],
                # FIXME - this is incorrect if this is a new problem; otherwise we could
                # just count the iterations
                "attempts": 1,
                "status": iteration_status,
                "bug_hunting_cycles": [],
            }
        ]

        self.next_state.flag_iterations_as_modified()
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

        llm = self.get_llm(TROUBLESHOOTER_GET_RUN_COMMAND)
        convo = self._get_task_convo().template("get_run_command")

        # Although the prompt is explicit about not using "```", LLM may still return it
        llm_response: str = await llm(convo, temperature=0, parser=OptionalCodeBlockParser())
        self.next_state.run_command = llm_response
        return llm_response

    async def get_user_instructions(self) -> Optional[str]:
        await self.send_message("Determining how to test the app ...")

        route_files = await self._get_route_files()

        llm = self.get_llm(stream_output=True)
        convo = self._get_task_convo().template(
            "define_user_review_goal", task=self.current_state.current_task, route_files=route_files
        )
        user_instructions: str = await llm(convo)

        user_instructions = user_instructions.strip()
        if user_instructions.lower() == "done":
            log.debug(f"Nothing to do for user testing for task {self.current_state.current_task['description']}")
            return None

        return user_instructions

    async def _get_route_files(self) -> list[File]:
        """Returns the list of file paths that have routes defined in them."""

        llm = self.get_llm()
        convo = AgentConvo(self).template("get_route_files").require_schema(RouteFilePaths)
        file_list = await llm(convo, parser=JSONParser(RouteFilePaths))
        route_files: set[str] = set(file_list.files)

        # Sometimes LLM can return a non-existent file, let's make sure to filter those out
        return [f for f in self.current_state.files if f.path in route_files]

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
        feedback (eg. if they just clicked on "Continue" or "Start Pair Programming").
        """

        bug_report = None
        change_description = None
        is_loop = False
        should_iterate = True

        test_message = "Please check if the app is working"
        if user_instructions:
            hint = " Here is a description of what should be working:\n\n" + user_instructions

        if run_command:
            await self.ui.send_run_command(run_command)

        buttons = {
            "continue": "Everything works",
            "change": "I want to make a change",
            "bug": "There is an issue",
            "start_pair_programming": "Start Pair Programming",
        }

        user_response = await self.ask_question(
            test_message, buttons=buttons, default="continue", buttons_only=True, hint=hint
        )
        if user_response.button == "continue" or user_response.cancelled:
            should_iterate = False

        elif user_response.button == "start_pair_programming":
            await telemetry.trace_code_event(
                "pair-programming-started",
                {
                    "clicked": True,
                    "task_index": self.current_state.tasks.index(self.current_state.current_task) + 1,
                    "num_tasks": len(self.current_state.tasks),
                    "num_epics": len(self.current_state.epics),
                    "num_iterations": len(self.current_state.iterations),
                    "num_steps": len(self.current_state.steps),
                    "architecture": {
                        "system_dependencies": self.current_state.specification.system_dependencies,
                        "app_dependencies": self.current_state.specification.package_dependencies,
                    },
                },
            )
            is_loop = True

        elif user_response.button == "change":
            user_description = await self.ask_question("Please describe the change you want to make (one at a time)")
            change_description = user_description.text

        elif user_response.button == "bug":
            user_description = await self.ask_question("Please describe the issue you found (one at a time)")
            bug_report = user_description.text

        return should_iterate, is_loop, bug_report, change_description

    def try_next_alternative_solution(self, user_feedback: str, user_feedback_qa: list[str]) -> AgentResponse:
        """
        Call the ProblemSolver to try an alternative solution.

        Stores the user feedback and sets iteration state so that ProblemSolver will be triggered.

        :param user_feedback: User feedback to store in the iteration state.
        :param user_feedback_qa: Additional questions/answers about the problem.
        :return: Agent response done.
        """
        next_state_iteration = self.next_state.iterations[-1]
        next_state_iteration["description"] = ""
        next_state_iteration["user_feedback"] = user_feedback
        next_state_iteration["user_feedback_qa"] = user_feedback_qa
        next_state_iteration["attempts"] += 1
        next_state_iteration["status"] = IterationStatus.PROBLEM_SOLVER
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
        llm = self.get_llm(stream_output=True)
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
