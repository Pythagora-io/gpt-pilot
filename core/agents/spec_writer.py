from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.db.models import Complexity
from core.llm.parser import StringParser
from core.telemetry import telemetry
from core.templates.example_project import (
    EXAMPLE_PROJECT_ARCHITECTURE,
    EXAMPLE_PROJECT_DESCRIPTION,
    EXAMPLE_PROJECT_PLAN,
)

# If the project description is less than this, perform an analysis using LLM
ANALYZE_THRESHOLD = 1500
# URL to the wiki page with tips on how to write a good project description
INITIAL_PROJECT_HOWTO_URL = (
    "https://github.com/Pythagora-io/gpt-pilot/wiki/How-to-write-a-good-initial-project-description"
)
SPEC_STEP_NAME = "Create specification"


class SpecWriter(BaseAgent):
    agent_type = "spec-writer"
    display_name = "Spec Writer"

    async def run(self) -> AgentResponse:
        response = await self.ask_question(
            "Describe your app in as much detail as possible",
            allow_empty=False,
            buttons={
                # FIXME: must be lowercase becase VSCode doesn't recognize it otherwise. Needs a fix in the extension
                "continue": "continue",
                "example": "Start an example project",
                "import": "Import an existing project",
            },
        )
        if response.cancelled:
            return AgentResponse.error(self, "No project description")

        if response.button == "import":
            return AgentResponse.import_project(self)

        if response.button == "example":
            await self.send_message("Starting example project with description:")
            await self.send_message(EXAMPLE_PROJECT_DESCRIPTION)
            self.prepare_example_project()
            return AgentResponse.done(self)
        elif response.button == "continue":
            # FIXME: Workaround for the fact that VSCode "continue" button does
            # nothing but repeat the question. We reproduce this bug for bug here.
            return AgentResponse.done(self)

        spec = response.text

        complexity = await self.check_prompt_complexity(spec)
        if len(spec) < ANALYZE_THRESHOLD and complexity != Complexity.SIMPLE:
            spec = await self.analyze_spec(spec)
            spec = await self.review_spec(spec)

        self.next_state.specification = self.current_state.specification.clone()
        self.next_state.specification.description = spec
        self.next_state.specification.complexity = complexity
        telemetry.set("initial_prompt", spec)
        telemetry.set("is_complex_app", complexity != Complexity.SIMPLE)

        self.next_state.action = SPEC_STEP_NAME
        return AgentResponse.done(self)

    async def check_prompt_complexity(self, prompt: str) -> str:
        await self.send_message("Checking the complexity of the prompt ...")
        llm = self.get_llm()
        convo = AgentConvo(self).template("prompt_complexity", prompt=prompt)
        llm_response: str = await llm(convo, temperature=0, parser=StringParser())
        return llm_response.lower()

    def prepare_example_project(self):
        spec = self.current_state.specification.clone()
        spec.description = EXAMPLE_PROJECT_DESCRIPTION
        spec.architecture = EXAMPLE_PROJECT_ARCHITECTURE["architecture"]
        spec.system_dependencies = EXAMPLE_PROJECT_ARCHITECTURE["system_dependencies"]
        spec.package_dependencies = EXAMPLE_PROJECT_ARCHITECTURE["package_dependencies"]
        spec.template = EXAMPLE_PROJECT_ARCHITECTURE["template"]
        spec.complexity = Complexity.SIMPLE
        telemetry.set("initial_prompt", spec.description.strip())
        telemetry.set("is_complex_app", False)
        telemetry.set("template", spec.template)
        telemetry.set(
            "architecture",
            {
                "architecture": spec.architecture,
                "system_dependencies": spec.system_dependencies,
                "package_dependencies": spec.package_dependencies,
            },
        )
        self.next_state.specification = spec

        self.next_state.epics = [
            {
                "name": "Initial Project",
                "description": EXAMPLE_PROJECT_DESCRIPTION,
                "completed": False,
                "complexity": Complexity.SIMPLE,
            }
        ]
        self.next_state.tasks = EXAMPLE_PROJECT_PLAN

    async def analyze_spec(self, spec: str) -> str:
        msg = (
            "Your project description seems a bit short. "
            "The better you can describe the project, the better GPT Pilot will understand what you'd like to build.\n\n"
            f"Here are some tips on how to better describe the project: {INITIAL_PROJECT_HOWTO_URL}\n\n"
            "Let's start by refining your project idea:"
        )
        await self.send_message(msg)

        llm = self.get_llm()
        convo = AgentConvo(self).template("ask_questions").user(spec)

        while True:
            response: str = await llm(convo)
            if len(response) > 500:
                # The response is too long for it to be a question, assume it's the spec
                confirm = await self.ask_question(
                    (
                        "Can we proceed with this project description? If so, just press ENTER. "
                        "Otherwise, please tell me what's missing or what you'd like to add."
                    ),
                    allow_empty=True,
                    buttons={"continue": "continue"},
                )
                if confirm.cancelled or confirm.button == "continue" or confirm.text == "":
                    return spec
                convo.user(confirm.text)

            else:
                convo.assistant(response)

                user_response = await self.ask_question(
                    response,
                    buttons={"skip": "Skip questions"},
                )
                if user_response.cancelled or user_response.button == "skip":
                    convo.user(
                        "This is enough clarification, you have all the information. "
                        "Please output the spec now, without additional comments or questions."
                    )
                    response: str = await llm(convo)
                    return response

                convo.user(user_response.text)

    async def review_spec(self, spec: str) -> str:
        convo = AgentConvo(self).template("review_spec", spec=spec)
        llm = self.get_llm()
        llm_response: str = await llm(convo, temperature=0)
        additional_info = llm_response.strip()
        if additional_info:
            spec += "\nAdditional info/examples:\n" + additional_info
        return spec
