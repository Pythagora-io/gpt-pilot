from enum import Enum
from typing import Annotated, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.mixins import RelevantFilesMixin
from core.agents.response import AgentResponse, ResponseType
from core.config import TASK_BREAKDOWN_AGENT_NAME
from core.db.models.project_state import IterationStatus, TaskStatus
from core.db.models.specification import Complexity
from core.llm.parser import JSONParser
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)


class StepType(str, Enum):
    COMMAND = "command"
    SAVE_FILE = "save_file"
    HUMAN_INTERVENTION = "human_intervention"


class CommandOptions(BaseModel):
    command: str = Field(description="Command to run")
    timeout: int = Field(description="Timeout in seconds")
    success_message: str = ""


class SaveFileOptions(BaseModel):
    path: str


class SaveFileStep(BaseModel):
    type: Literal[StepType.SAVE_FILE] = StepType.SAVE_FILE
    save_file: SaveFileOptions


class CommandStep(BaseModel):
    type: Literal[StepType.COMMAND] = StepType.COMMAND
    command: CommandOptions


class HumanInterventionStep(BaseModel):
    type: Literal[StepType.HUMAN_INTERVENTION] = StepType.HUMAN_INTERVENTION
    human_intervention_description: str


Step = Annotated[
    Union[SaveFileStep, CommandStep, HumanInterventionStep],
    Field(discriminator="type"),
]


class TaskSteps(BaseModel):
    steps: list[Step]


class Developer(RelevantFilesMixin, BaseAgent):
    agent_type = "developer"
    display_name = "Developer"

    async def run(self) -> AgentResponse:
        if self.prev_response and self.prev_response.type == ResponseType.TASK_REVIEW_FEEDBACK:
            return await self.breakdown_current_iteration(self.prev_response.data["feedback"])

        if not self.current_state.unfinished_tasks:
            log.warning("No unfinished tasks found, nothing to do (why am I called? is this a bug?)")
            return AgentResponse.done(self)

        if self.current_state.unfinished_iterations:
            return await self.breakdown_current_iteration()

        # By default, we want to ask the user if they want to run the task,
        # except in certain cases (such as they've just edited it).
        # The check for docs is here to prevent us from asking the user whether we should
        # run the task twice - we'll only ask if we haven't yet checked for docs.
        if not self.current_state.current_task.get("run_always", False) and self.current_state.docs is None:
            if not await self.ask_to_execute_task():
                return AgentResponse.done(self)

        if self.current_state.docs is None and self.current_state.specification.complexity != Complexity.SIMPLE:
            # We check for external docs here, to make sure we only fetch the docs
            # if the task is actually being done.
            return AgentResponse.external_docs_required(self)

        return await self.breakdown_current_task()

    async def breakdown_current_iteration(self, task_review_feedback: Optional[str] = None) -> AgentResponse:
        """
        Breaks down current iteration or task review into steps.

        :param task_review_feedback: If provided, the task review feedback is broken down instead of the current iteration
        :return: AgentResponse.done(self) when the breakdown is done
        """
        current_task = self.current_state.current_task

        if task_review_feedback is not None:
            iteration = None
            current_task["task_review_feedback"] = task_review_feedback
            description = task_review_feedback
            user_feedback = ""
            source = "review"
            n_tasks = 1
            log.debug(f"Breaking down the task review feedback {task_review_feedback}")
            await self.send_message("Breaking down the task review feedback...")
        elif self.current_state.current_iteration["status"] in (
            IterationStatus.AWAITING_BUG_FIX,
            IterationStatus.AWAITING_LOGGING,
        ):
            iteration = self.current_state.current_iteration
            current_task["task_review_feedback"] = None

            description = iteration["bug_hunting_cycles"][-1]["human_readable_instructions"]
            user_feedback = iteration["user_feedback"]
            source = "bug_hunt"
            n_tasks = len(self.next_state.iterations)
            log.debug(f"Breaking down the logging cycle {description}")
            await self.send_message("Breaking down the current bug hunting cycle ...")
        else:
            iteration = self.current_state.current_iteration
            current_task["task_review_feedback"] = None
            if iteration is None:
                log.error("Iteration breakdown called but there's no current iteration or task review, possible bug?")
                return AgentResponse.done(self)

            description = iteration["description"]
            user_feedback = iteration["user_feedback"]
            source = "troubleshooting"
            n_tasks = len(self.next_state.iterations)
            log.debug(f"Breaking down the iteration {description}")
            await self.send_message("Breaking down the current task iteration ...")

        if self.current_state.files and self.current_state.relevant_files is None:
            return await self.get_relevant_files(user_feedback, description)

        await self.ui.send_task_progress(
            n_tasks,  # iterations and reviews can be created only one at a time, so we are always on last one
            n_tasks,
            current_task["description"],
            source,
            "in-progress",
            self.current_state.get_source_index(source),
            self.current_state.tasks,
        )
        llm = self.get_llm()
        # FIXME: In case of iteration, parse_task depends on the context (files, tasks, etc) set there.
        # Ideally this prompt would be self-contained.
        convo = (
            AgentConvo(self)
            .template(
                "iteration",
                user_feedback=user_feedback,
                user_feedback_qa=None,
                next_solution_to_try=None,
                docs=self.current_state.docs,
            )
            .assistant(description)
            .template("parse_task")
            .require_schema(TaskSteps)
        )
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        self.set_next_steps(response, source)

        if iteration:
            if "status" not in iteration or (
                iteration["status"] in (IterationStatus.AWAITING_USER_TEST, IterationStatus.AWAITING_BUG_REPRODUCTION)
            ):
                # This is just a support for old iterations that don't have status
                self.next_state.complete_iteration()
                self.next_state.action = f"Troubleshooting #{len(self.current_state.iterations)}"
            elif iteration["status"] == IterationStatus.IMPLEMENT_SOLUTION:
                # If the user requested a change, then, we'll implement it and go straight back to testing
                self.next_state.complete_iteration()
                self.next_state.action = f"Troubleshooting #{len(self.current_state.iterations)}"
            elif iteration["status"] == IterationStatus.AWAITING_BUG_FIX:
                # If bug fixing is done, ask user to test again
                self.next_state.current_iteration["status"] = IterationStatus.AWAITING_USER_TEST
            elif iteration["status"] == IterationStatus.AWAITING_LOGGING:
                # If logging is done, ask user to reproduce the bug
                self.next_state.current_iteration["status"] = IterationStatus.AWAITING_BUG_REPRODUCTION
        else:
            self.next_state.action = "Task review feedback"

        current_task_index = self.current_state.tasks.index(current_task)
        self.next_state.tasks[current_task_index] = {
            **current_task,
        }
        self.next_state.flag_tasks_as_modified()
        return AgentResponse.done(self)

    async def breakdown_current_task(self) -> AgentResponse:
        current_task = self.current_state.current_task
        current_task["task_review_feedback"] = None
        source = self.current_state.current_epic.get("source", "app")
        await self.ui.send_task_progress(
            self.current_state.tasks.index(current_task) + 1,
            len(self.current_state.tasks),
            current_task["description"],
            source,
            "in-progress",
            self.current_state.get_source_index(source),
            self.current_state.tasks,
        )

        log.debug(f"Breaking down the current task: {current_task['description']}")
        await self.send_message("Thinking about how to implement this task ...")

        log.debug(f"Current state files: {len(self.current_state.files)}, relevant {self.current_state.relevant_files}")
        # Check which files are relevant to the current task
        if self.current_state.files and self.current_state.relevant_files is None:
            return await self.get_relevant_files()

        current_task_index = self.current_state.tasks.index(current_task)

        llm = self.get_llm(TASK_BREAKDOWN_AGENT_NAME, stream_output=True)
        convo = AgentConvo(self).template(
            "breakdown",
            task=current_task,
            iteration=None,
            current_task_index=current_task_index,
            docs=self.current_state.docs,
        )
        response: str = await llm(convo)

        await self.get_relevant_files(None, response)

        self.next_state.tasks[current_task_index] = {
            **current_task,
            "instructions": response,
        }
        self.next_state.flag_tasks_as_modified()

        llm = self.get_llm()
        convo.assistant(response).template("parse_task").require_schema(TaskSteps)
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        # There might be state leftovers from previous tasks that we need to clean here
        self.next_state.modified_files = {}
        self.set_next_steps(response, source)
        self.next_state.action = f"Task #{current_task_index + 1} start"
        await telemetry.trace_code_event(
            "task-start",
            {
                "task_index": current_task_index + 1,
                "num_tasks": len(self.current_state.tasks),
                "num_epics": len(self.current_state.epics),
            },
        )
        return AgentResponse.done(self)

    def set_next_steps(self, response: TaskSteps, source: str):
        # For logging/debugging purposes, we don't want to remove the finished steps
        # until we're done with the task.
        finished_steps = [step for step in self.current_state.steps if step["completed"]]
        self.next_state.steps = finished_steps + [
            {
                "id": uuid4().hex,
                "completed": False,
                "source": source,
                "iteration_index": len(self.current_state.iterations),
                **step.model_dump(),
            }
            for step in response.steps
        ]
        if (
            len(self.next_state.unfinished_steps) > 0
            and source != "review"
            and (
                self.next_state.current_iteration is None
                or self.next_state.current_iteration["status"] != IterationStatus.AWAITING_LOGGING
            )
        ):
            self.next_state.steps += [
                # TODO: add refactor step here once we have the refactor agent
                {
                    "id": uuid4().hex,
                    "completed": False,
                    "type": "review_task",
                    "source": source,
                    "iteration_index": len(self.current_state.iterations),
                },
            ]
        log.debug(f"Next steps: {self.next_state.unfinished_steps}")

    async def ask_to_execute_task(self) -> bool:
        """
        Asks the user to approve, skip or edit the current task.

        If task is edited, the method returns False so that the changes are saved. The
        Orchestrator will rerun the agent on the next iteration.

        :return: True if the task should be executed as is, False if the task is skipped or edited
        """
        buttons = {"yes": "Yes", "edit": "Edit Task"}
        if len(self.current_state.tasks) > 1:
            buttons["skip"] = "Skip Task"

        description = self.current_state.current_task["description"]
        await self.send_message("Starting new task with description:\n\n" + description)
        user_response = await self.ask_question(
            "Do you want to execute the above task?",
            buttons=buttons,
            default="yes",
            buttons_only=True,
            hint=description,
        )
        if user_response.button == "yes":
            # Execute the task as is
            return True

        if user_response.cancelled or user_response.button == "skip":
            log.info(f"Skipping task: {description}")
            self.next_state.current_task["instructions"] = "(skipped on user request)"
            self.next_state.set_current_task_status(TaskStatus.SKIPPED)
            await self.send_message("Skipping task...")
            # We're done here, and will pick up the next task (if any) on the next run
            return False

        user_response = await self.ask_question(
            "Edit the task description:",
            buttons={
                # FIXME: must be lowercase becase VSCode doesn't recognize it otherwise. Needs a fix in the extension
                "continue": "continue",
                "cancel": "Cancel",
            },
            default="continue",
            initial_text=description,
        )
        if user_response.button == "cancel" or user_response.cancelled:
            # User hasn't edited the task so we can execute it immediately as is
            return await self.ask_to_execute_task()

        self.next_state.current_task["description"] = user_response.text
        self.next_state.current_task["run_always"] = True
        self.next_state.relevant_files = None
        log.info(f"Task description updated to: {user_response.text}")
        # Orchestrator will rerun us with the new task description
        return False
