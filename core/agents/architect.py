import json
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.db.models import Specification
from core.llm.parser import JSONParser
from core.log import get_logger
from core.telemetry import telemetry
from core.templates.base import BaseProjectTemplate, NoOptions
from core.templates.example_project import EXAMPLE_PROJECTS
from core.templates.registry import (
    PROJECT_TEMPLATES,
    ProjectTemplateEnum,
)

ARCHITECTURE_STEP_NAME = "Project architecture"
WARN_SYSTEM_DEPS = ["docker", "kubernetes", "microservices"]
WARN_FRAMEWORKS = ["next.js", "vue", "vue.js", "svelte", "angular"]
WARN_FRAMEWORKS_URL = "https://github.com/Pythagora-io/gpt-pilot/wiki/Using-GPT-Pilot-with-frontend-frameworks"

log = get_logger(__name__)


class AppType(str, Enum):
    WEB = "web-app"
    API = "api-service"
    MOBILE = "mobile-app"
    DESKTOP = "desktop-app"
    CLI = "cli-tool"


# FIXME: all the reponse pydantic models should be strict (see config._StrictModel), also check if we
# can disallow adding custom Python attributes to the model
class SystemDependency(BaseModel):
    name: str = Field(
        None,
        description="Name of the system dependency, for example Node.js or Python.",
    )
    description: str = Field(
        None,
        description="One-line description of the dependency.",
    )
    test: str = Field(
        None,
        description="Command line to test whether the dependency is available on the system.",
    )
    required_locally: bool = Field(
        None,
        description="Whether this dependency must be installed locally (as opposed to connecting to cloud or other server)",
    )


class PackageDependency(BaseModel):
    name: str = Field(
        None,
        description="Name of the package dependency, for example Express or React.",
    )
    description: str = Field(
        None,
        description="One-line description of the dependency.",
    )


class Architecture(BaseModel):
    app_type: AppType = Field(
        AppType.WEB,
        description="Type of the app to build.",
    )
    system_dependencies: list[SystemDependency] = Field(
        None,
        description="List of system dependencies required to build and run the app.",
    )
    package_dependencies: list[PackageDependency] = Field(
        None,
        description="List of framework/language-specific packages used by the app.",
    )


class TemplateSelection(BaseModel):
    architecture: str = Field(
        None,
        description="General description of the app architecture.",
    )
    template: Optional[ProjectTemplateEnum] = Field(
        None,
        description="Project template to use for the app, or null if no template is a good fit.",
    )


class Architect(BaseAgent):
    agent_type = "architect"
    display_name = "Architect"

    async def run(self) -> AgentResponse:
        spec = self.current_state.specification.clone()

        if spec.example_project:
            self.prepare_example_project(spec)
        else:
            await self.plan_architecture(spec)

        await self.check_system_dependencies(spec)

        self.next_state.specification = spec
        telemetry.set("templates", spec.templates)
        self.next_state.action = ARCHITECTURE_STEP_NAME
        return AgentResponse.done(self)

    async def select_templates(self, spec: Specification) -> tuple[str, dict[ProjectTemplateEnum, Any]]:
        """
        Select project template(s) to use based on the project description.

        Although the Pythagora database models support multiple projects, this
        function will choose at most one project template, as we currently don't
        have templates that could be used together in a single project.

        :param spec: Project specification.
        :return: Dictionary of selected project templates.
        """
        await self.send_message("Selecting starter templates ...")

        llm = self.get_llm()
        convo = (
            AgentConvo(self)
            .template(
                "select_templates",
                templates=PROJECT_TEMPLATES,
            )
            .require_schema(TemplateSelection)
        )
        tpl: TemplateSelection = await llm(convo, parser=JSONParser(TemplateSelection))
        templates = {}
        # if tpl.template:
        #     answer = await self.ask_question(
        #         f"Do you want to use the '{tpl.template.name}' template?",
        #         buttons={"yes": "Yes", "no": "No"},
        #         default="yes",
        #         buttons_only=True,
        #         hint="Project templates are here to speed up start of your app development and save tokens and time.\n"
        #         "Choose 'Yes' to use suggested template for your app.\n"
        #         "If you choose 'No', project will be created from scratch.",
        #     )
        #
        #     if answer.button == "no":
        #         return tpl.architecture, templates
        #
        #     template_class = PROJECT_TEMPLATES.get(tpl.template)
        #     if template_class:
        #         options = await self.configure_template(spec, template_class)
        #         templates[tpl.template] = template_class(
        #             options,
        #             self.state_manager,
        #             self.process_manager,
        #         )

        return tpl.architecture, templates

    async def plan_architecture(self, spec: Specification):
        await self.send_message("Planning project architecture ...")
        architecture_description, templates = await self.select_templates(spec)

        await self.send_message("Picking technologies to use ...")

        llm = self.get_llm(stream_output=True)
        convo = (
            AgentConvo(self)
            .template(
                "technologies",
                templates=templates,
                architecture=architecture_description,
            )
            .require_schema(Architecture)
        )
        arch: Architecture = await llm(convo, parser=JSONParser(Architecture))

        await self.check_compatibility(arch)

        spec.architecture = architecture_description
        spec.templates = {t.name: t.options_dict for t in templates.values()}
        spec.system_dependencies = [d.model_dump() for d in arch.system_dependencies]
        spec.package_dependencies = [d.model_dump() for d in arch.package_dependencies]
        telemetry.set("architecture", json.loads(arch.model_dump_json()))

    async def check_compatibility(self, arch: Architecture) -> bool:
        warn_system_deps = [dep.name for dep in arch.system_dependencies if dep.name.lower() in WARN_SYSTEM_DEPS]
        warn_package_deps = [dep.name for dep in arch.package_dependencies if dep.name.lower() in WARN_FRAMEWORKS]

        if warn_system_deps:
            await self.ask_question(
                f"Warning: Pythagora doesn't officially support {', '.join(warn_system_deps)}. "
                f"You can try to use {'it' if len(warn_system_deps) == 1 else 'them'}, but you may run into problems.",
                buttons={"continue": "Continue"},
                buttons_only=True,
                default="continue",
            )

        if warn_package_deps:
            await self.ask_question(
                f"Warning: Pythagora works best with vanilla JavaScript. "
                f"You can try try to use {', '.join(warn_package_deps)}, but you may run into problems. "
                f"Visit {WARN_FRAMEWORKS_URL} for more information.",
                buttons={"continue": "Continue"},
                buttons_only=True,
                default="continue",
            )

        # TODO: add "cancel" option to the above buttons; if pressed, Architect should
        # return AgentResponse.revise_spec()
        # that SpecWriter should catch and allow the user to reword the initial spec.
        return True

    def prepare_example_project(self, spec: Specification):
        log.debug(f"Setting architecture for example project: {spec.example_project}")
        arch = EXAMPLE_PROJECTS[spec.example_project]["architecture"]

        spec.architecture = arch["architecture"]
        spec.system_dependencies = arch["system_dependencies"]
        spec.package_dependencies = arch["package_dependencies"]
        spec.templates = arch["templates"]
        telemetry.set("templates", spec.templates)

    async def check_system_dependencies(self, spec: Specification):
        """
        Check whether the required system dependencies are installed.

        This also stores the app architecture telemetry data, including the
        information about whether each system dependency is installed.

        :param spec: Project specification.
        """
        deps = spec.system_dependencies

        for dep in deps:
            await self.send_message(f"Checking if {dep['name']} is available ...")
            status_code, _, _ = await self.process_manager.run_command(dep["test"])
            dep["installed"] = bool(status_code == 0)
            if status_code != 0:
                if dep["required_locally"]:
                    remedy = "Please install it before proceeding with your app."
                else:
                    remedy = "If you would like to use it locally, please install it before proceeding."
                await self.send_message(f"❌ {dep['name']} is not available. {remedy}")
                await self.ask_question(
                    "",
                    buttons={"continue": f"I've installed {dep['name']}"},
                    buttons_only=True,
                    default="continue",
                )

            else:
                await self.send_message(f"✅ {dep['name']} is available.")

    async def configure_template(self, spec: Specification, template_class: BaseProjectTemplate) -> BaseModel:
        """
        Ask the LLM to configure the template options.

        Based on the project description, the LLM should pick the options that
        make the most sense. If template has no options, the method is a no-op
        and returns an empty options model.

        :param spec: Project specification.
        :param template_class: Template that needs to be configured.
        :return: Configured options model.
        """
        if template_class.options_class is NoOptions:
            # If template has no options, no need to ask LLM for anything
            return NoOptions()

        llm = self.get_llm(stream_output=True)
        convo = (
            AgentConvo(self)
            .template(
                "configure_template",
                project_description=spec.description,
                project_template=template_class,
            )
            .require_schema(template_class.options_class)
        )
        return await llm(convo, parser=JSONParser(template_class.options_class))
