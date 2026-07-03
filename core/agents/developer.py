import json
from enum import Enum
from typing import Annotated, Literal, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.mixins import ChatWithBreakdownMixin, RelevantFilesMixin
from core.agents.response import AgentResponse
from core.cli.helpers import get_epic_task_number
from core.config import PARSE_TASK_AGENT_NAME, TASK_BREAKDOWN_AGENT_NAME
from core.config.actions import (
    DEV_EXECUTE_TASK,
    DEV_TASK_BREAKDOWN,
    DEV_TASK_REVIEW_FEEDBACK,
    DEV_TASK_START,
    DEV_TROUBLESHOOT,
    DEV_WAIT_TEST,
)
from core.db.models.project_state import IterationStatus, TaskStatus
from core.db.models.specification import Complexity
from core.llm.parser import JSONParser
from core.log import get_logger
from core.memory import ProjectMemory
from core.telemetry import telemetry
from core.ui.base import ProjectStage, pythagora_source

log = get_logger(__name__)


class StepType(str, Enum):
    COMMAND = "command"
    SAVE_FILE = "save_file"
    HUMAN_INTERVENTION = "human_intervention"
    UTILITY_FUNCTION = "utility_function"


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


class UtilityFunction(BaseModel):
    type: Literal[StepType.UTILITY_FUNCTION] = StepType.UTILITY_FUNCTION
    file: str
    function_name: str
    description: str
    return_value: str
    input_value: str
    status: Literal["mocked", "implemented"]


Step = Annotated[
    Union[SaveFileStep, CommandStep, HumanInterventionStep, UtilityFunction],
    Field(discriminator="type"),
]


class TaskSteps(BaseModel):
    steps: list[Step]


def has_correct_num_of_tags(response: str) -> bool:
    """
    Checks if the response has the correct number of opening and closing tags.
    """
    return response.count("<pythagoracode file") == response.count("</pythagoracode>")


class Developer(ChatWithBreakdownMixin, RelevantFilesMixin, BaseAgent):
    agent_type = "developer"
    display_name = "Developer"

    async def run(self) -> AgentResponse:
        if self.current_state.current_step and self.current_state.current_step.get("type") == "utility_function":
            return await self.update_knowledge_base()

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

    async def breakdown_current_iteration(self) -> AgentResponse:
        """
        Breaks down current iteration or task review into steps.

        :return: AgentResponse.done(self) when the breakdown is done
        """
        current_task = self.current_state.current_task

        if self.current_state.current_iteration["status"] in (
            IterationStatus.AWAITING_BUG_FIX,
            IterationStatus.AWAITING_LOGGING,
        ):
            iteration = self.current_state.current_iteration

            description = iteration["bug_hunting_cycles"][-1]["human_readable_instructions"]
            user_feedback = iteration["user_feedback"]
            source = "bug_hunt"
            n_tasks = len(self.next_state.iterations)
            log.debug(f"Breaking down the logging cycle {description}")
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

        if self.current_state.files and self.current_state.relevant_files is None:
            await self.get_relevant_files_parallel(user_feedback, description)

        await self.ui.send_task_progress(
            n_tasks,  # iterations and reviews can be created only one at a time, so we are always on last one
            n_tasks,
            current_task["description"],
            source,
            "in-progress",
            self.current_state.get_source_index(source),
            self.current_state.tasks,
        )
        llm = self.get_llm(PARSE_TASK_AGENT_NAME)

        # FIXME: In case of iteration, parse_task depends on the context (files, tasks, etc) set there.
        #  Ideally this prompt would be self-contained.

        convo = (
            AgentConvo(self).template("parse_task", implementation_instructions=description).require_schema(TaskSteps)
        )
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        self.set_next_steps(response, source)

        if iteration:
            if "status" not in iteration or (
                iteration["status"] in (IterationStatus.AWAITING_USER_TEST, IterationStatus.AWAITING_BUG_REPRODUCTION)
            ):
                # This is just a support for old iterations that don't have status
                self.next_state.complete_iteration()
                self.next_state.action = DEV_TROUBLESHOOT.format(len(self.current_state.iterations))
            elif iteration["status"] == IterationStatus.IMPLEMENT_SOLUTION:
                # If the user requested a change, then, we'll implement it and go straight back to testing
                self.next_state.complete_iteration()
                self.next_state.action = DEV_TROUBLESHOOT.format(len(self.current_state.iterations))
            elif iteration["status"] == IterationStatus.AWAITING_BUG_FIX:
                # If bug fixing is done, ask user to test again
                self.next_state.action = DEV_WAIT_TEST
                self.next_state.current_iteration["status"] = IterationStatus.AWAITING_USER_TEST
            elif iteration["status"] == IterationStatus.AWAITING_LOGGING:
                # If logging is done, ask user to reproduce the bug
                self.next_state.current_iteration["status"] = IterationStatus.AWAITING_BUG_REPRODUCTION
        else:
            self.next_state.action = DEV_TASK_REVIEW_FEEDBACK

        current_task_index = self.current_state.tasks.index(current_task)
        self.next_state.tasks[current_task_index] = {
            **current_task,
        }
        self.next_state.flag_tasks_as_modified()
        return AgentResponse.done(self)

    async def _recall_project_memory(self, task_description: str) -> list:
        """
        Recall decisions/bug-fixes from earlier sessions relevant to the current task.

        Returns an empty list when the optional Dakera memory integration is disabled
        or unavailable, in which case the breakdown prompt is unchanged.
        """
        memory = ProjectMemory.for_project(self.state_manager.project.id)
        if memory is None:
            return []
        memories = await memory.recall(task_description)
        if memories:
            log.debug(f"Injecting {len(memories)} recalled memories into task breakdown")
        return memories

    async def breakdown_current_task(self) -> AgentResponse:
        current_task = self.current_state.current_task
        current_task_index = self.current_state.tasks.index(current_task)
        self.next_state.action = DEV_TASK_BREAKDOWN.format(current_task_index + 1)

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

        log.debug(f"Current state files: {len(self.current_state.files)}, relevant {self.current_state.relevant_files}")
        # Check which files are relevant to the current task
        await self.get_relevant_files_parallel()

        current_task_index = self.current_state.tasks.index(current_task)

        await self.send_message("### Thinking about how to implement this task ...")

        await self.ui.start_breakdown_stream()
        await self.ui.set_important_stream()
        related_api_endpoints = current_task.get("related_api_endpoints", [])
        llm = self.get_llm(TASK_BREAKDOWN_AGENT_NAME, stream_output=True)
        # TODO: Temp fix for old projects
        if not (
            related_api_endpoints
            and len(related_api_endpoints) > 0
            and all(isinstance(api, dict) and "endpoint" in api for api in related_api_endpoints)
        ):
            related_api_endpoints = []

        redo_task_user_feedback = None

        if (
            self.next_state
            and self.next_state.current_task
            and self.next_state.current_task.get("redo_human_instructions", None) is not None
        ):
            redo_task_user_feedback = self.next_state.current_task["redo_human_instructions"]

        dakera_memories = await self._recall_project_memory(current_task["description"])

        convo = AgentConvo(self).template(
            "breakdown",
            task=current_task,
            iteration=None,
            current_task_index=current_task_index,
            docs=self.current_state.docs,
            related_api_endpoints=related_api_endpoints,
            redo_task_user_feedback=redo_task_user_feedback,
            dakera_memories=dakera_memories,
        )

        response: str = await llm(convo)

        convo.assistant(response)

        max_retries = 2
        retry_count = 0

        while retry_count < max_retries:
            if has_correct_num_of_tags(response):
                break

            convo.user(
                "Ok, now think carefully about your previous response. If the response ends by mentioning something about continuing with the implementation, continue but don't implement any files that have already been implemented. If your last response finishes with an incomplete file, implement that file and any other that needs implementation. Finally, if your last response doesn't end by mentioning continuing and if there isn't an unfinished file implementation, respond only with `DONE` and with nothing else."
            )
            continue_response: str = await llm(convo)

            last_open_tag_index = response.rfind("<pythagoracode file")
            response = response[:last_open_tag_index] + continue_response

            convo.assistant(response)

            retry_count += 1

        response = await self.chat_with_breakdown(convo, response)

        self.next_state.tasks[current_task_index] = {
            **current_task,
            "instructions": response,
        }
        self.next_state.flag_tasks_as_modified()

        llm = self.get_llm(PARSE_TASK_AGENT_NAME)

        convo = AgentConvo(self).template("parse_task", implementation_instructions=response).require_schema(TaskSteps)

        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        # There might be state leftovers from previous tasks that we need to clean here
        self.next_state.modified_files = {}
        self.set_next_steps(response, source)
        self.next_state.current_task["status"] = TaskStatus.IN_PROGRESS
        self.next_state.action = DEV_TASK_START.format(current_task_index + 1)
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
        unique_steps = self.remove_duplicate_steps({**response.model_dump()})
        finished_steps = [step for step in self.current_state.steps if step["completed"]]
        self.next_state.steps = finished_steps + [
            {
                "id": uuid4().hex,
                "completed": False,
                "source": source,
                "iteration_index": len(self.current_state.iterations),
                **step,
            }
            for step in unique_steps["steps"]
        ]
        log.debug(f"Next steps: {self.next_state.unfinished_steps}")

    def remove_duplicate_steps(self, data):
        unique_steps = []

        # Process steps attribute
        for step in data["steps"]:
            if isinstance(step, SaveFileStep) and any(
                s["type"] == "save_file" and s["save_file"]["path"] == step["save_file"]["path"] for s in unique_steps
            ):
                continue
            unique_steps.append(step)

        # Update steps attribute
        data["steps"] = unique_steps

        # Use the serializable_steps for JSON dumping
        data["original_response"] = json.dumps(unique_steps, indent=2)

        return data

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
        epic_index, task_index = get_epic_task_number(self.current_state, self.current_state.current_task)

        await self.ui.send_project_stage(
            {
                "stage": ProjectStage.STARTING_TASK,
                "task_index": task_index,
            }
        )

        # find latest finished task, send back logs for it being finished
        tasks_done = [task for task in self.current_state.tasks if task not in self.current_state.unfinished_tasks]
        previous_task = tasks_done[-1] if tasks_done else None
        if previous_task:
            e_i, t_i = get_epic_task_number(self.current_state, previous_task)
            task_convo = await self.state_manager.get_task_conversation_project_states(
                UUID(previous_task["id"]), first_last_only=True
            )
            await self.ui.send_back_logs(
                [
                    {
                        "title": previous_task["description"],
                        "project_state_id": str(task_convo[0].id) if task_convo else "be_0",
                        "start_id": str(task_convo[0].id) if task_convo else "be_0",
                        "end_id": str(task_convo[-1].prev_state_id) if task_convo else "be_0",
                        "labels": [f"E{e_i} / T{t_i}", "Backend", "done"],
                    }
                ]
            )
            await self.ui.send_front_logs_headers(
                str(task_convo[0].id) if task_convo else "be_0",
                [f"E{e_i} / T{t_i}", "Backend", "done"],
                previous_task["description"],
                self.current_state.current_task.get("id"),
            )

        await self.ui.send_front_logs_headers(
            str(self.current_state.id),
            [f"E{epic_index} / T{task_index}", "Backend", "working"],
            description,
            self.current_state.current_task.get("id"),
        )

        await self.ui.send_back_logs(
            [
                {
                    "title": description,
                    "project_state_id": str(self.current_state.id),
                    "labels": [f"E{epic_index} / T{task_index}", "working"],
                }
            ]
        )
        await self.ui.clear_main_logs()
        await self.send_message(f"Starting task #{task_index} with the description:\n\n## {description}")
        if self.current_state.run_command:
            await self.ui.send_run_command(self.current_state.run_command)

        if self.next_state.current_task.get("redo_human_instructions", None) is not None:
            await self.send_message(f"Additional feedback: {self.next_state.current_task['redo_human_instructions']}")
            return True

        if self.current_state.current_task.get("quick_implementation", False):
            return True

        if self.current_state.current_task.get("user_added_subsequently", False):
            return True

        if self.current_state.current_task.get("hardcoded", False):
            return True

        if self.current_state.current_task and self.current_state.current_task.get("hardcoded", False):
            await self.ui.send_message(
                "Ok, great, you're now starting to build the backend and the first task is to test how the authentication works. You can now register and login. Your data will be saved into the database.",
                source=pythagora_source,
            )

        user_response = await self.ask_question(
            DEV_EXECUTE_TASK,
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
            # User hasn't edited the task, so we can execute it immediately as is
            return await self.ask_to_execute_task()

        self.next_state.current_task["description"] = user_response.text
        self.next_state.current_task["run_always"] = True
        self.next_state.relevant_files = None
        log.info(f"Task description updated to: {user_response.text}")
        # Orchestrator will rerun us with the new task description
        return False

    async def update_knowledge_base(self):
        """
        Update the knowledge base with the current task and steps.
        """
        await self.state_manager.update_utility_functions(self.current_state.current_step)
        self.next_state.complete_step("utility_function")
        return AgentResponse.done(self)
