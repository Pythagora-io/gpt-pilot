from enum import Enum
from typing import Annotated, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse, ResponseType
from core.db.models.project_state import TaskStatus
from core.llm.parser import JSONParser
from core.log import get_logger

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


class RelevantFiles(BaseModel):
    relevant_files: list[str] = Field(description="List of relevant files for the current task.")


class Developer(BaseAgent):
    agent_type = "developer"
    display_name = "Developer"

    async def run(self) -> AgentResponse:
        if self.prev_response and self.prev_response.type == ResponseType.TASK_REVIEW_FEEDBACK:
            return await self.breakdown_current_iteration(self.prev_response.data["feedback"])

        # If any of the files are missing metadata/descriptions, those need to be filled-in
        missing_descriptions = [file.path for file in self.current_state.files if not file.meta.get("description")]
        if missing_descriptions:
            log.debug(f"Some files are missing descriptions: {', '.join(missing_descriptions)}, reqesting analysis")
            return AgentResponse.describe_files(self)

        log.debug(
            f"Current state files: {len(self.current_state.files)}, relevant {self.current_state.relevant_files or []}"
        )
        # Check which files are relevant to the current task
        if self.current_state.files and self.current_state.relevant_files is None:
            await self.get_relevant_files()
            return AgentResponse.done(self)

        if not self.current_state.unfinished_tasks:
            log.warning("No unfinished tasks found, nothing to do (why am I called? is this a bug?)")
            return AgentResponse.done(self)

        if self.current_state.unfinished_iterations:
            return await self.breakdown_current_iteration()

        # By default, we want to ask the user if they want to run the task,
        # except in certain cases (such as they've just edited it).
        if not self.current_state.current_task.get("run_always", False):
            if not await self.ask_to_execute_task():
                return AgentResponse.done(self)

        return await self.breakdown_current_task()

    async def breakdown_current_iteration(self, review_feedback: Optional[str] = None) -> AgentResponse:
        """
        Breaks down current iteration or task review into steps.

        :param review_feedback: If provided, the task review feedback is broken down instead of the current iteration
        :return: AgentResponse.done(self) when the breakdown is done
        """

        if review_feedback is not None:
            iteration = None
            description = review_feedback
            user_feedback = ""
            source = "review"
            n_tasks = 1
            log.debug(f"Breaking down the task review feedback {review_feedback}")
            await self.send_message("Breaking down the task review feedback...")
        else:
            iteration = self.current_state.current_iteration
            if iteration is None:
                log.error("Iteration breakdown called but there's no current iteration or task review, possible bug?")
                return AgentResponse.done(self)

            description = iteration["description"]
            user_feedback = iteration["user_feedback"]
            source = "troubleshooting"
            n_tasks = len(self.next_state.iterations)
            log.debug(f"Breaking down the iteration {description}")
            await self.send_message("Breaking down the current task iteration ...")

        await self.get_relevant_files(user_feedback, description)

        await self.ui.send_task_progress(
            n_tasks,  # iterations and reviews can be created only one at a time, so we are always on last one
            n_tasks,
            self.current_state.current_task["description"],
            source,
            "in-progress",
        )
        llm = self.get_llm()
        # FIXME: In case of iteration, parse_task depends on the context (files, tasks, etc) set there.
        # Ideally this prompt would be self-contained.
        convo = (
            AgentConvo(self)
            .template(
                "iteration",
                current_task=self.current_state.current_task,
                user_feedback=user_feedback,
                user_feedback_qa=None,
                next_solution_to_try=None,
            )
            .assistant(description)
            .template("parse_task")
            .require_schema(TaskSteps)
        )
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        self.set_next_steps(response, source)

        if iteration:
            self.next_state.complete_iteration()
            self.next_state.action = f"Troubleshooting #{len(self.current_state.iterations)}"
        else:
            self.next_state.action = "Task review feedback"

        return AgentResponse.done(self)

    async def breakdown_current_task(self) -> AgentResponse:
        task = self.current_state.current_task
        source = self.current_state.current_epic.get("source", "app")
        await self.ui.send_task_progress(
            self.current_state.tasks.index(self.current_state.current_task) + 1,
            len(self.current_state.tasks),
            self.current_state.current_task["description"],
            source,
            "in-progress",
        )

        log.debug(f"Breaking down the current task: {task['description']}")
        await self.send_message("Thinking about how to implement this task ...")

        current_task_index = self.current_state.tasks.index(task)

        llm = self.get_llm()
        convo = AgentConvo(self).template(
            "breakdown",
            task=task,
            iteration=None,
            current_task_index=current_task_index,
        )
        response: str = await llm(convo)

        # FIXME: check if this is correct, as sqlalchemy can't figure out modifications
        # to attributes; however, self.next is not saved yet so maybe this is fine
        self.next_state.tasks[current_task_index] = {
            **task,
            "instructions": response,
        }

        await self.send_message("Breaking down the task into steps ...")
        convo.assistant(response).template("parse_task").require_schema(TaskSteps)
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        # There might be state leftovers from previous tasks that we need to clean here
        self.next_state.modified_files = {}
        self.set_next_steps(response, source)
        self.next_state.action = f"Task #{current_task_index + 1} start"
        return AgentResponse.done(self)

    async def get_relevant_files(
        self, user_feedback: Optional[str] = None, solution_description: Optional[str] = None
    ) -> AgentResponse:
        log.debug("Getting relevant files for the current task")
        await self.send_message("Figuring out which project files are relevant for the next task ...")

        llm = self.get_llm()
        convo = (
            AgentConvo(self)
            .template(
                "filter_files",
                current_task=self.current_state.current_task,
                user_feedback=user_feedback,
                solution_description=solution_description,
            )
            .require_schema(RelevantFiles)
        )

        llm_response: list[str] = await llm(convo, parser=JSONParser(RelevantFiles), temperature=0)

        existing_files = {file.path for file in self.current_state.files}
        self.next_state.relevant_files = [path for path in llm_response.relevant_files if path in existing_files]

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
                **step.model_dump(),
            }
            for step in response.steps
        ]
        if len(self.next_state.unfinished_steps) > 0 and source != "review":
            self.next_state.steps += [
                # TODO: add refactor step here once we have the refactor agent
                {
                    "id": uuid4().hex,
                    "completed": False,
                    "type": "review_task",
                    "source": source,
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
        await self.send_message("Starting new task with description:")
        await self.send_message(description)
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
            return True

        self.next_state.current_task["description"] = user_response.text
        self.next_state.current_task["run_always"] = True
        self.next_state.relevant_files = None
        log.info(f"Task description updated to: {user_response.text}")
        # Orchestrator will rerun us with the new task description
        return False
