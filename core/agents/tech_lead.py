import json
from uuid import uuid4

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.mixins import RelevantFilesMixin
from core.agents.response import AgentResponse
from core.config import TECH_LEAD_EPIC_BREAKDOWN, TECH_LEAD_PLANNING
from core.db.models import Complexity
from core.db.models.project_state import TaskStatus
from core.llm.parser import JSONParser
from core.log import get_logger
from core.telemetry import telemetry
from core.templates.registry import PROJECT_TEMPLATES
from core.ui.base import ProjectStage, pythagora_source, success_source

log = get_logger(__name__)


class APIEndpoint(BaseModel):
    description: str = Field(description="Description of an API endpoint.")
    method: str = Field(description="HTTP method of the API endpoint.")
    endpoint: str = Field(description="URL of the API endpoint.")
    request_body: dict = Field(description="Request body of the API endpoint.")
    response_body: dict = Field(description="Response body of the API endpoint.")


class Epic(BaseModel):
    description: str = Field(description="Description of an epic.")


class Task(BaseModel):
    description: str = Field(description="Description of a task.")
    related_api_endpoints: list[APIEndpoint] = Field(description="API endpoints that will be implemented in this task.")
    testing_instructions: str = Field(description="Instructions for testing the task.")


class DevelopmentPlan(BaseModel):
    plan: list[Epic] = Field(description="List of epics that need to be done to implement the entire plan.")


class EpicPlan(BaseModel):
    plan: list[Task] = Field(description="List of tasks that need to be done to implement the entire epic.")


class TechLead(RelevantFilesMixin, BaseAgent):
    agent_type = "tech-lead"
    display_name = "Tech Lead"

    async def run(self) -> AgentResponse:
        # Building frontend is the first epic
        if len(self.current_state.epics) == 1:
            self.create_initial_project_epic()
            return AgentResponse.done(self)

        # if self.current_state.specification.templates and len(self.current_state.files) < 2:
        #     await self.apply_project_templates()
        #     self.next_state.action = "Apply project templates"
        #     await self.ui.send_epics_and_tasks(
        #         self.next_state.current_epic["sub_epics"],
        #         self.next_state.tasks,
        #     )
        #
        #     inputs = []
        #     for file in self.next_state.files:
        #         input_required = self.state_manager.get_input_required(file.content.content)
        #         if input_required:
        #             inputs += [{"file": file.path, "line": line} for line in input_required]
        #
        #     if inputs:
        #         return AgentResponse.input_required(self, inputs)
        #     else:
        #         return AgentResponse.done(self)

        if self.current_state.current_epic:
            self.next_state.action = "Create a development plan"
            return await self.plan_epic(self.current_state.current_epic)
        else:
            return await self.ask_for_new_feature()

    def create_initial_project_epic(self):
        log.debug("Creating initial project Epic")
        self.next_state.epics = self.current_state.epics + [
            {
                "id": uuid4().hex,
                "name": "Initial Project",
                "source": "app",
                "description": self.current_state.specification.description,
                "test_instructions": None,
                "summary": None,
                "completed": False,
                "complexity": self.current_state.specification.complexity,
                "sub_epics": [],
            }
        ]
        self.next_state.relevant_files = None
        self.next_state.modified_files = {}

    async def apply_project_templates(self):
        state = self.current_state
        summaries = []

        # Only do this for the initial project and if the templates are specified
        if len(state.epics) != 1 or not state.specification.templates:
            return

        for template_name, template_options in state.specification.templates.items():
            template_class = PROJECT_TEMPLATES.get(template_name)
            if not template_class:
                log.error(f"Project template not found: {template_name}")
                continue

            template = template_class(
                template_options,
                self.state_manager,
                self.process_manager,
            )

            description = template.description
            log.info(f"Applying project template: {template.name}")
            await self.send_message(f"Applying project template {description} ...")
            summary = await template.apply()
            summaries.append(summary)

        # Saving template files will fill this in and we want it clear for the first task.
        self.next_state.relevant_files = None

        if summaries:
            spec = self.current_state.specification.clone()
            spec.template_summary = "\n\n".join(summaries)

            self.next_state.specification = spec

    async def ask_for_new_feature(self) -> AgentResponse:
        if len(self.current_state.epics) > 2:
            await self.ui.send_message("Your new feature is complete!", source=success_source)
        else:
            await self.ui.send_message("Your app is DONE! You can start using it right now!", source=success_source)

        if self.current_state.run_command:
            await self.ui.send_run_command(self.current_state.run_command)

        log.debug("Asking for new feature")
        response = await self.ask_question(
            "Do you have a new feature to add to the project? Just write it here:",
            buttons={"continue": "continue", "end": "No, I'm done"},
            allow_empty=False,
            extra_info="restart_app",
        )

        if response.button == "end" or response.cancelled or not response.text:
            await self.ui.send_message("Thank you for using Pythagora!", source=pythagora_source)
            return AgentResponse.exit(self)

        feature_description = response.text
        self.next_state.epics = self.current_state.epics + [
            {
                "id": uuid4().hex,
                "name": f"Feature #{len(self.current_state.epics)}",
                "test_instructions": None,
                "source": "feature",
                "description": feature_description,
                "summary": None,
                "completed": False,
                "complexity": None,  # Determined and defined in SpecWriter
                "sub_epics": [],
            }
        ]
        # Orchestrator will rerun us to break down the new feature epic
        self.next_state.action = f"Start of feature #{len(self.current_state.epics)}"
        return AgentResponse.update_specification(self, feature_description)

    async def plan_epic(self, epic) -> AgentResponse:
        log.debug(f"Planning tasks for the epic: {epic['name']}")
        await self.send_message("Creating the development plan ...")

        if epic.get("source") == "feature":
            await self.get_relevant_files(user_feedback=epic.get("description"))

        llm = self.get_llm(TECH_LEAD_PLANNING)
        convo = (
            AgentConvo(self)
            .template(
                "plan",
                epic=epic,
                task_type=self.current_state.current_epic.get("source", "app"),
                # FIXME: we're injecting summaries to initial description
                existing_summary=None,
                get_only_api_files=True,
            )
            .require_schema(DevelopmentPlan)
        )

        response: DevelopmentPlan = await llm(convo, parser=JSONParser(DevelopmentPlan))

        convo.remove_last_x_messages(1)
        formatted_epics = [f"Epic #{index}: {epic.description}" for index, epic in enumerate(response.plan, start=1)]
        epics_string = "\n\n".join(formatted_epics)
        convo = convo.assistant(epics_string)
        llm = self.get_llm(TECH_LEAD_EPIC_BREAKDOWN)

        if epic.get("source") == "feature" or epic.get("complexity") == Complexity.SIMPLE:
            await self.send_message(f"Epic 1: {epic['name']}")
            self.next_state.current_epic["sub_epics"] = [
                {
                    "id": 1,
                    "description": epic["name"],
                }
            ]
            await self.send_message("Creating tasks for this epic ...")
            self.next_state.tasks = self.next_state.tasks + [
                {
                    "id": uuid4().hex,
                    "description": task.description,
                    "instructions": None,
                    "pre_breakdown_testing_instructions": None,
                    "status": TaskStatus.TODO,
                    "sub_epic_id": 1,
                }
                for task in response.plan
            ]
        else:
            self.next_state.current_epic["sub_epics"] = [
                {
                    "id": sub_epic_number,
                    "description": sub_epic.description,
                }
                for sub_epic_number, sub_epic in enumerate(response.plan, start=1)
            ]
            for sub_epic_number, sub_epic in enumerate(response.plan, start=1):
                await self.send_message(f"Epic {sub_epic_number}: {sub_epic.description}")
                convo = convo.template(
                    "epic_breakdown",
                    epic_number=sub_epic_number,
                    epic_description=sub_epic.description,
                    get_only_api_files=True,
                ).require_schema(EpicPlan)
                await self.send_message("Creating tasks for this epic ...")
                epic_plan: EpicPlan = await llm(convo, parser=JSONParser(EpicPlan))
                self.next_state.tasks = self.next_state.tasks + [
                    {
                        "id": uuid4().hex,
                        "description": task.description,
                        "instructions": None,
                        "pre_breakdown_testing_instructions": task.testing_instructions,
                        "status": TaskStatus.TODO,
                        "sub_epic_id": sub_epic_number,
                        "related_api_endpoints": [rae.model_dump() for rae in (task.related_api_endpoints or [])],
                    }
                    for task in epic_plan.plan
                ]
                convo.remove_last_x_messages(2)

        await self.ui.send_epics_and_tasks(
            self.next_state.current_epic["sub_epics"],
            self.next_state.tasks,
        )

        await self.ui.send_project_stage({"stage": ProjectStage.OPEN_PLAN})
        response = await self.ask_question(
            "Open and edit your development plan in the Progress tab",
            buttons={"done_editing": "I'm done editing, the plan looks good"},
            default="done_editing",
            buttons_only=True,
            extra_info="edit_plan",
        )

        self.update_epics_and_tasks(response.text)

        await self.ui.send_epics_and_tasks(
            self.next_state.current_epic["sub_epics"],
            self.next_state.tasks,
        )

        await telemetry.trace_code_event(
            "development-plan",
            {
                "num_tasks": len(self.current_state.tasks),
                "num_epics": len(self.current_state.epics),
            },
        )
        return AgentResponse.done(self)

    def update_epics_and_tasks(self, edited_plan_string):
        edited_plan = json.loads(edited_plan_string)
        updated_tasks = []

        existing_tasks_map = {task["description"]: task for task in self.next_state.tasks}

        self.next_state.current_epic["sub_epics"] = []
        for sub_epic_number, sub_epic in enumerate(edited_plan, start=1):
            self.next_state.current_epic["sub_epics"].append(
                {
                    "id": sub_epic_number,
                    "description": sub_epic["description"],
                }
            )

            for task in sub_epic["tasks"]:
                original_task = existing_tasks_map.get(task["description"])
                if original_task and task == original_task:
                    updated_task = original_task.copy()
                    updated_task["sub_epic_id"] = sub_epic_number
                    updated_tasks.append(updated_task)
                else:
                    updated_tasks.append(
                        {
                            "id": uuid4().hex,
                            "description": task["description"],
                            "instructions": None,
                            "pre_breakdown_testing_instructions": None,
                            "status": TaskStatus.TODO,
                            "sub_epic_id": sub_epic_number,
                        }
                    )

        self.next_state.tasks = updated_tasks
