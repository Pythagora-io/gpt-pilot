from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse, ResponseType
from core.config import SPEC_WRITER_AGENT_NAME
from core.db.models import Complexity
from core.db.models.project_state import IterationStatus
from core.llm.parser import StringParser
from core.log import get_logger
from core.telemetry import telemetry

# If the project description is less than this, perform an analysis using LLM
ANALYZE_THRESHOLD = 1500
# URL to the wiki page with tips on how to write a good project description
INITIAL_PROJECT_HOWTO_URL = (
    "https://github.com/Pythagora-io/gpt-pilot/wiki/How-to-write-a-good-initial-project-description"
)
SPEC_STEP_NAME = "Create specification"

log = get_logger(__name__)


class SpecWriter(BaseAgent):
    agent_type = "spec-writer"
    display_name = "Spec Writer"

    async def run(self) -> AgentResponse:
        current_iteration = self.current_state.current_iteration
        if current_iteration is not None and current_iteration.get("status") == IterationStatus.NEW_FEATURE_REQUESTED:
            return await self.update_spec(iteration_mode=True)
        elif self.prev_response and self.prev_response.type == ResponseType.UPDATE_SPECIFICATION:
            return await self.update_spec(iteration_mode=False)
        else:
            return await self.initialize_spec()

    async def initialize_spec(self) -> AgentResponse:
        # response = await self.ask_question(
        #     "Describe your app in as much detail as possible",
        #     allow_empty=False,
        # )
        # if response.cancelled:
        #     return AgentResponse.error(self, "No project description")
        #
        # user_description = response.text.strip()
        user_description = self.current_state.epics[0]["description"]

        complexity = await self.check_prompt_complexity(user_description)
        await telemetry.trace_code_event(
            "project-description",
            {
                "initial_prompt": user_description,
                "complexity": complexity,
            },
        )

        reviewed_spec = user_description
        # if len(user_description) < ANALYZE_THRESHOLD and complexity != Complexity.SIMPLE:
        #     initial_spec = await self.analyze_spec(user_description)
        #     reviewed_spec = await self.review_spec(desc=user_description, spec=initial_spec)

        self.next_state.specification = self.current_state.specification.clone()
        self.next_state.specification.original_description = user_description
        self.next_state.specification.description = reviewed_spec
        self.next_state.specification.complexity = complexity
        telemetry.set("initial_prompt", user_description)
        telemetry.set("updated_prompt", reviewed_spec)
        telemetry.set("is_complex_app", complexity != Complexity.SIMPLE)

        self.next_state.action = SPEC_STEP_NAME
        return AgentResponse.done(self)

    async def update_spec(self, iteration_mode) -> AgentResponse:
        if iteration_mode:
            feature_description = self.current_state.current_iteration["user_feedback"]
        else:
            feature_description = self.prev_response.data["description"]

        await self.send_message(
            f"Making the following changes to project specification:\n\n{feature_description}\n\nUpdated project specification:"
        )
        llm = self.get_llm(SPEC_WRITER_AGENT_NAME, stream_output=True)
        convo = AgentConvo(self).template("add_new_feature", feature_description=feature_description)
        llm_response: str = await llm(convo, temperature=0, parser=StringParser())
        updated_spec = llm_response.strip()
        await self.ui.generate_diff(
            "project_specification", self.current_state.specification.description, updated_spec, source=self.ui_source
        )
        user_response = await self.ask_question(
            "Do you accept these changes to the project specification?",
            buttons={"yes": "Yes", "no": "No"},
            default="yes",
            buttons_only=True,
        )
        await self.ui.close_diff()

        if user_response.button == "yes":
            self.next_state.specification = self.current_state.specification.clone()
            self.next_state.specification.description = updated_spec
            telemetry.set("updated_prompt", updated_spec)

        if iteration_mode:
            self.next_state.current_iteration["status"] = IterationStatus.FIND_SOLUTION
            self.next_state.flag_iterations_as_modified()
        else:
            complexity = await self.check_prompt_complexity(feature_description)
            self.next_state.current_epic["complexity"] = complexity

        return AgentResponse.done(self)

    async def check_prompt_complexity(self, prompt: str) -> str:
        is_feature = self.current_state.epics and len(self.current_state.epics) > 2
        await self.send_message("Checking the complexity of the prompt ...")
        llm = self.get_llm(SPEC_WRITER_AGENT_NAME)
        convo = AgentConvo(self).template(
            "prompt_complexity",
            prompt=prompt,
            is_feature=is_feature,
        )
        llm_response: str = await llm(convo, temperature=0, parser=StringParser())
        log.info(f"Complexity check response: {llm_response}")
        return llm_response.lower()

    async def analyze_spec(self, spec: str) -> str:
        msg = (
            "Your project description seems a bit short. "
            "The better you can describe the project, the better Pythagora will understand what you'd like to build.\n\n"
            f"Here are some tips on how to better describe the project: {INITIAL_PROJECT_HOWTO_URL}\n\n"
            "Let's start by refining your project idea:"
        )
        await self.send_message(msg)

        llm = self.get_llm(SPEC_WRITER_AGENT_NAME, stream_output=True)
        convo = AgentConvo(self).template("ask_questions").user(spec)
        n_questions = 0
        n_answers = 0

        while True:
            response: str = await llm(convo)
            if len(response) > 500:
                # The response is too long for it to be a question, assume it's the updated spec
                confirm = await self.ask_question(
                    ("Would you like to change or add anything? Write it out here."),
                    allow_empty=True,
                    buttons={"continue": "No thanks, the spec looks good"},
                )
                if confirm.cancelled or confirm.button == "continue" or confirm.text == "":
                    updated_spec = response.strip()
                    await telemetry.trace_code_event(
                        "spec-writer-questions",
                        {
                            "num_questions": n_questions,
                            "num_answers": n_answers,
                            "new_spec": updated_spec,
                        },
                    )
                    return updated_spec
                convo.user(confirm.text)

            else:
                convo.assistant(response)

                n_questions += 1
                user_response = await self.ask_question(
                    response,
                    buttons={"skip": "Skip this question", "skip_all": "No more questions"},
                    verbose=False,
                )
                if user_response.cancelled or user_response.button == "skip_all":
                    convo.user(
                        "This is enough clarification, you have all the information. "
                        "Please output the spec now, without additional comments or questions."
                    )
                    response: str = await llm(convo)
                    confirm = await self.ask_question(
                        ("Would you like to change or add anything? Write it out here."),
                        allow_empty=True,
                        buttons={"continue": "No thanks, the spec looks good"},
                    )
                    if confirm.cancelled or confirm.button == "continue" or confirm.text == "":
                        updated_spec = response.strip()
                        await telemetry.trace_code_event(
                            "spec-writer-questions",
                            {
                                "num_questions": n_questions,
                                "num_answers": n_answers,
                                "new_spec": updated_spec,
                            },
                        )
                        return updated_spec
                    convo.user(confirm.text)
                    continue

                n_answers += 1
                if user_response.button == "skip":
                    convo.user("Skip this question.")
                    continue
                else:
                    convo.user(user_response.text)

    async def review_spec(self, desc: str, spec: str) -> str:
        convo = AgentConvo(self).template("review_spec", desc=desc, spec=spec)
        llm = self.get_llm(SPEC_WRITER_AGENT_NAME)
        llm_response: str = await llm(convo, temperature=0)
        additional_info = llm_response.strip()
        if additional_info and len(additional_info) > 6:
            spec += "\n\nAdditional info/examples:\n\n" + additional_info
            await self.send_message(f"\n\nAdditional info/examples:\n\n {additional_info}")

        return spec
