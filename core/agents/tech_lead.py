from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.db.models import Complexity
from core.db.models.project_state import TaskStatus
from core.llm.parser import JSONParser
from core.log import get_logger
from core.templates.registry import apply_project_template, get_template_description, get_template_summary
from core.ui.base import ProjectStage, success_source

log = get_logger(__name__)


class Task(BaseModel):
    description: str = Field(description=("Very detailed description of a development task."))


class DevelopmentPlan(BaseModel):
    plan: list[Task] = Field(description="List of development tasks that need to be done to implement the entire plan.")


class UpdatedDevelopmentPlan(BaseModel):
    updated_current_task: Task = Field(
        description="Updated detailed description of what was implemented while working on the current development task."
    )
    plan: list[Task] = Field(description="List of unfinished development tasks.")


class TechLead(BaseAgent):
    agent_type = "tech-lead"
    display_name = "Tech Lead"

    async def run(self) -> AgentResponse:
        current_task_status = self.current_state.current_task.get("status") if self.current_state.current_task else None
        if current_task_status and current_task_status == TaskStatus.DOCUMENTED:
            return await self.update_epic()

        if len(self.current_state.epics) == 0:
            self.create_initial_project_epic()
            # Orchestrator will rerun us to break down the initial project epic
            return AgentResponse.done(self)

        await self.ui.send_project_stage(ProjectStage.CODING)

        if self.current_state.specification.template and not self.current_state.files:
            await self.apply_project_template()
            self.next_state.action = "Apply project template"
            return AgentResponse.done(self)

        if self.current_state.current_epic:
            self.next_state.action = "Create a development plan"
            return await self.plan_epic(self.current_state.current_epic)
        else:
            return await self.ask_for_new_feature()

    def create_initial_project_epic(self):
        log.debug("Creating initial project epic")
        self.next_state.epics = [
            {
                "id": uuid4().hex,
                "name": "Initial Project",
                "source": "app",
                "description": self.current_state.specification.description,
                "test_instructions": None,
                "summary": None,
                "completed": False,
                "complexity": self.current_state.specification.complexity,
            }
        ]

    async def apply_project_template(self) -> Optional[str]:
        state = self.current_state

        # Only do this for the initial project and if the template is specified
        if len(state.epics) != 1 or not state.specification.template:
            return None

        description = get_template_description(state.specification.template)
        log.info(f"Applying project template: {state.specification.template}")
        await self.send_message(f"Applying project template {description} ...")
        summary = await apply_project_template(
            self.current_state.specification.template,
            self.state_manager,
            self.process_manager,
        )
        # Saving template files will fill this in and we want it clear for the
        # first task.
        self.next_state.relevant_files = None
        return summary

    async def ask_for_new_feature(self) -> AgentResponse:
        if len(self.current_state.epics) > 2:
            await self.ui.send_message("Your new feature is complete!", source=success_source)
        else:
            await self.ui.send_message("Your app is DONE!!! You can start using it right now!", source=success_source)

        log.debug("Asking for new feature")
        response = await self.ask_question(
            "Do you have a new feature to add to the project? Just write it here",
            buttons={"continue": "continue", "end": "No, I'm done"},
            allow_empty=True,
        )

        if response.cancelled or not response.text:
            return AgentResponse.exit(self)

        self.next_state.epics = self.current_state.epics + [
            {
                "id": uuid4().hex,
                "name": f"Feature #{len(self.current_state.epics)}",
                "test_instructions": None,
                "source": "feature",
                "description": response.text,
                "summary": None,
                "completed": False,
                "complexity": Complexity.HARD,
            }
        ]
        # Orchestrator will rerun us to break down the new feature epic
        self.next_state.action = f"Start of feature #{len(self.current_state.epics)}"
        return AgentResponse.done(self)

    async def plan_epic(self, epic) -> AgentResponse:
        log.debug(f"Planning tasks for the epic: {epic['name']}")
        await self.send_message("Starting to create the action plan for development ...")

        llm = self.get_llm()
        convo = (
            AgentConvo(self)
            .template(
                "plan",
                epic=epic,
                task_type=self.current_state.current_epic.get("source", "app"),
                existing_summary=get_template_summary(self.current_state.specification.template),
            )
            .require_schema(DevelopmentPlan)
        )

        response: DevelopmentPlan = await llm(convo, parser=JSONParser(DevelopmentPlan))
        self.next_state.tasks = self.current_state.tasks + [
            {
                "id": uuid4().hex,
                "description": task.description,
                "instructions": None,
                "status": TaskStatus.TODO,
            }
            for task in response.plan
        ]
        return AgentResponse.done(self)

    async def update_epic(self) -> AgentResponse:
        """
        Update the development plan for the current epic.
        """
        epic = self.current_state.current_epic
        self.next_state.set_current_task_status(TaskStatus.EPIC_UPDATED)

        if len(self.next_state.unfinished_tasks) == 1 or not self.current_state.iterations:
            # Current task is still "unfinished" at this point, so if it's last task, there's nothing to update
            return AgentResponse.done(self)

        finished_tasks = [task for task in self.next_state.tasks if task["status"] == TaskStatus.DONE]
        finished_tasks.append(self.next_state.current_task)

        log.debug(f"Updating development plan for {epic['name']}")
        await self.send_message("Updating development plan ...")

        llm = self.get_llm()
        convo = (
            AgentConvo(self)
            .template(
                "update_plan",
                finished_tasks=finished_tasks,
                task_type=self.current_state.current_epic.get("source", "app"),
                modified_files=[f for f in self.current_state.files if f.path in self.current_state.modified_files],
            )
            .require_schema(UpdatedDevelopmentPlan)
        )

        response: UpdatedDevelopmentPlan = await llm(
            convo,
            parser=JSONParser(UpdatedDevelopmentPlan),
            temperature=0,
        )
        log.debug(f"Reworded last task as: {response.updated_current_task.description}")
        finished_tasks[-1]["description"] = response.updated_current_task.description

        self.next_state.tasks = finished_tasks + [
            {
                "id": uuid4().hex,
                "description": task.description,
                "instructions": None,
                "status": TaskStatus.TODO,
            }
            for task in response.plan
        ]
        log.debug(f"Updated development plan for {epic['name']}, {len(response.plan)} tasks remaining")
        return AgentResponse.done(self)
