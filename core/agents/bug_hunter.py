from enum import Enum

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import CHECK_LOGS_AGENT_NAME, magic_words
from core.db.models.project_state import IterationStatus
from core.llm.parser import JSONParser
from core.log import get_logger

log = get_logger(__name__)


class StepType(str, Enum):
    ADD_LOG = "add_log"
    EXPLAIN_PROBLEM = "explain_problem"
    GET_ADDITIONAL_FILES = "get_additional_files"


class HuntConclusionType(str, Enum):
    ADD_LOGS = magic_words.ADD_LOGS
    PROBLEM_IDENTIFIED = magic_words.PROBLEM_IDENTIFIED


class HuntConclusionOptions(BaseModel):
    conclusion: HuntConclusionType = Field(
        description=f"If more logs are needed to identify the problem, respond with '{magic_words.ADD_LOGS}'. If the problem is identified, respond with '{magic_words.PROBLEM_IDENTIFIED}'."
    )


class ImportantLog(BaseModel):
    logCode: str = Field(description="Actual line of code that prints the log.")
    filePath: str = Field(description="Path to the file in which the log exists.")
    currentOutput: str = Field(description="Current output of the log.")
    expectedOutput: str = Field(description="Expected output of the log.")
    explanation: str = Field(description="A brief explanation of the log.")


class ImportantLogsForDebugging(BaseModel):
    logs: list[ImportantLog] = Field(description="Important logs that will help the human debug the current bug.")


class BugHunter(BaseAgent):
    agent_type = "bug-hunter"
    display_name = "Bug Hunter"

    async def run(self) -> AgentResponse:
        current_iteration = self.current_state.current_iteration

        if "bug_reproduction_description" not in current_iteration:
            await self.get_bug_reproduction_instructions()
        if current_iteration["status"] == IterationStatus.HUNTING_FOR_BUG:
            # TODO determine how to find a bug (eg. check in db, ask user a question, etc.)
            return await self.check_logs()
        elif current_iteration["status"] == IterationStatus.AWAITING_USER_TEST:
            return await self.ask_user_to_test(False, True)
        elif current_iteration["status"] == IterationStatus.AWAITING_BUG_REPRODUCTION:
            return await self.ask_user_to_test(True, False)
        elif current_iteration["status"] == IterationStatus.START_PAIR_PROGRAMMING:
            return await self.start_pair_programming()

    async def get_bug_reproduction_instructions(self):
        llm = self.get_llm()
        convo = AgentConvo(self).template(
            "get_bug_reproduction_instructions",
            current_task=self.current_state.current_task,
            user_feedback=self.current_state.current_iteration["user_feedback"],
            user_feedback_qa=self.current_state.current_iteration["user_feedback_qa"],
            docs=self.current_state.docs,
            next_solution_to_try=None,
        )
        bug_reproduction_instructions = await llm(convo, temperature=0)
        self.next_state.current_iteration["bug_reproduction_description"] = bug_reproduction_instructions

    async def check_logs(self, logs_message: str = None):
        llm = self.get_llm(CHECK_LOGS_AGENT_NAME)
        convo = self.generate_iteration_convo_so_far()

        human_readable_instructions = await llm(convo, temperature=0.5)

        convo = (
            AgentConvo(self)
            .template(
                "bug_found_or_add_logs",
                hunt_conclusion=human_readable_instructions,
            )
            .require_schema(HuntConclusionOptions)
        )
        llm = self.get_llm()
        hunt_conclusion = await llm(convo, parser=JSONParser(HuntConclusionOptions), temperature=0)

        self.next_state.current_iteration["description"] = human_readable_instructions
        self.next_state.current_iteration["bug_hunting_cycles"] += [
            {
                "human_readable_instructions": human_readable_instructions,
                "fix_attempted": any(
                    c["fix_attempted"] for c in self.current_state.current_iteration["bug_hunting_cycles"]
                ),
            }
        ]

        if hunt_conclusion.conclusion == magic_words.PROBLEM_IDENTIFIED:
            # if no need for logs, implement iteration same as before
            self.next_state.current_iteration["status"] = IterationStatus.AWAITING_BUG_FIX
            await self.send_message("The bug is found - I'm  attempting to fix it.")
        else:
            # if logs are needed, add logging steps
            self.next_state.current_iteration["status"] = IterationStatus.AWAITING_LOGGING
            await self.send_message("Adding more logs to identify the bug.")

        self.next_state.flag_iterations_as_modified()
        return AgentResponse.done(self)

    async def ask_user_to_test(self, awaiting_bug_reproduction: bool = False, awaiting_user_test: bool = False):
        await self.send_message(
            "You can reproduce the bug like this:\n\n"
            + self.current_state.current_iteration["bug_reproduction_description"]
        )

        buttons = {}

        last_iteration = self.current_state.iterations[-1] if len(self.current_state.iterations) >= 3 else None
        if last_iteration:
            buttons["loop"] = "I'm stuck in a loop"

        if self.current_state.run_command:
            await self.ui.send_run_command(self.current_state.run_command)

        if awaiting_user_test:
            buttons["yes"] = "Yes, the issue is fixed"
            buttons["no"] = "No"
            user_feedback = await self.ask_question(
                "Is the bug you reported fixed now?",
                buttons=buttons,
                default="yes",
                buttons_only=True,
                hint="Instructions for testing:\n\n"
                + self.current_state.current_iteration["bug_reproduction_description"],
            )
            self.next_state.current_iteration["bug_hunting_cycles"][-1]["fix_attempted"] = True

            if user_feedback.button == "yes":
                self.next_state.complete_iteration()
            elif user_feedback.button == "loop":
                self.next_state.current_iteration["status"] = IterationStatus.START_PAIR_PROGRAMMING
            else:
                awaiting_bug_reproduction = True

        if awaiting_bug_reproduction:
            # TODO how can we get FE and BE logs automatically?
            buttons["continue"] = "Continue"
            buttons["done"] = "Bug is fixed"
            backend_logs = await self.ask_question(
                "Please do exactly what you did in the last iteration, paste **BACKEND** logs here and click CONTINUE.",
                buttons=buttons,
                default="continue",
                hint="Instructions for testing:\n\n"
                + self.current_state.current_iteration["bug_reproduction_description"],
            )

            if backend_logs.button == "done":
                self.next_state.complete_iteration()
            elif backend_logs.button == "loop":
                self.next_state.current_iteration["status"] = IterationStatus.START_PAIR_PROGRAMMING
            else:
                frontend_logs = await self.ask_question(
                    "Please paste **frontend** logs here and click CONTINUE.",
                    buttons={"continue": "Continue", "done": "Bug is fixed"},
                    default="continue",
                    hint="Instructions for testing:\n\n"
                    + self.current_state.current_iteration["bug_reproduction_description"],
                )

                # TODO select only the logs that are new (with PYTHAGORA_DEBUGGING_LOG)
                self.next_state.current_iteration["bug_hunting_cycles"][-1]["backend_logs"] = backend_logs.text
                self.next_state.current_iteration["bug_hunting_cycles"][-1]["frontend_logs"] = frontend_logs.text
                self.next_state.current_iteration["status"] = IterationStatus.HUNTING_FOR_BUG

                if frontend_logs.button == "done":
                    self.next_state.complete_iteration()

        return AgentResponse.done(self)

    async def start_pair_programming(self):
        llm = self.get_llm()
        convo = self.generate_iteration_convo_so_far(True)
        # TODO: structure this output better
        convo = convo.template("problem_explanation")
        initial_explanation = await llm(convo, temperature=0.5)

        convo = convo.template("data_about_logs").require_schema(ImportantLogsForDebugging)

        data_about_logs = await llm(convo, parser=JSONParser(ImportantLogsForDebugging), temperature=0.5)

        await self.ui.send_data_about_logs(data_about_logs)

        while True:
            self.next_state.current_iteration["initial_explanation"] = initial_explanation
            next_step = await self.ask_question(
                "How do you want to approach this?",
                buttons={
                    "question": "I have a question",
                    "done": "I fixed the bug myself",
                    "tell_me_more": "Tell me more about the bug",
                    "additional_user_info": "I have a hint for Pythagora",
                    "solution_tip": "I think I know where the problem is",
                    "other": "Other",
                },
                default="continue",
                hint="Instructions for testing:\n\n"
                + self.current_state.current_iteration["bug_reproduction_description"],
            )

            # TODO: remove when Leon checks
            convo.remove_last_x_messages(2)

            if len(convo.messages) > 10:
                convo.trim(1, 2)

            if next_step.button == "done":
                self.next_state.complete_iteration()
            elif next_step.button == "question":
                # TODO: in the future improve with a separate conversation and autonomous parsing of user info
                user_response = await self.ask_question("Oh, cool, what would you like to know?")
                convo = convo.template("ask_a_question", question=user_response.text)
                llm_answer = await llm(convo, temperature=0.5)
                await self.send_message(llm_answer)
            elif next_step.button == "tell_me_more":
                convo.template("tell_me_more")
                response = await llm(convo, temperature=0.5)
                await self.send_message(response)
            elif next_step.button == "other":
                # this is the same as "question" - we want to keep an option for users to click to understand if we're missing something with other options
                user_response = await self.ask_question("Let me know what you think...")
                convo = convo.template("ask_a_question", question=user_response.text)
                llm_answer = await llm(convo, temperature=0.5)
                await self.send_message(llm_answer)
            elif next_step.button in ["additional_user_info", "solution_tip"]:
                user_response = await self.ask_question("Oh, cool, what would you like to know?")
                await self.continue_on(convo, next_step.button, user_response)
            elif next_step.button == "tell_me_more":
                convo.template("tell_me_more")
                response = await llm(convo, temperature=0.5)
                await self.send_message(response)
                continue

            # TODO: send telemetry so we know what do users mostly click here!
            return AgentResponse.done(self)

    def generate_iteration_convo_so_far(self, omit_last_cycle=False):
        convo = AgentConvo(self).template(
            "iteration",
            current_task=self.current_state.current_task,
            user_feedback=self.current_state.current_iteration["user_feedback"],
            user_feedback_qa=self.current_state.current_iteration["user_feedback_qa"],
            docs=self.current_state.docs,
            magic_words=magic_words,
            next_solution_to_try=None,
        )

        hunting_cycles = self.current_state.current_iteration.get("bug_hunting_cycles", [])[
            0 : (-1 if omit_last_cycle else None)
        ]

        for hunting_cycle in hunting_cycles:
            convo = convo.assistant(hunting_cycle["human_readable_instructions"]).template(
                "log_data",
                backend_logs=hunting_cycle["backend_logs"],
                frontend_logs=hunting_cycle["frontend_logs"],
                fix_attempted=hunting_cycle["fix_attempted"],
            )

        return convo

    async def continue_on(self, convo, button_value, user_response):
        llm = self.get_llm()
        convo = convo.template("continue_on")
        continue_on = await llm(convo, temperature=0.5)
        return continue_on
