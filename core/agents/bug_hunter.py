from enum import Enum

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import CHECK_LOGS_AGENT_NAME, magic_words
from core.db.models.project_state import IterationStatus
from core.llm.parser import JSONParser
from core.log import get_logger
from core.telemetry import telemetry

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
    shouldBeDifferent: bool = Field(
        description="Whether the current output should be different from the expected output."
    )
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
        llm = self.get_llm(stream_output=True)
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
        llm = self.get_llm(CHECK_LOGS_AGENT_NAME, stream_output=True)
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
        llm = self.get_llm(stream_output=True)
        hunt_conclusion = await llm(convo, parser=JSONParser(HuntConclusionOptions), temperature=0)

        if hunt_conclusion.conclusion == magic_words.PROBLEM_IDENTIFIED:
            # if no need for logs, implement iteration same as before
            self.set_data_for_next_hunting_cycle(human_readable_instructions, IterationStatus.AWAITING_BUG_FIX)
            await self.send_message("Found the bug - I'm attempting to fix it ...")
        else:
            # if logs are needed, add logging steps
            self.set_data_for_next_hunting_cycle(human_readable_instructions, IterationStatus.AWAITING_LOGGING)
            await self.send_message("Adding more logs to identify the bug ...")

        self.next_state.flag_iterations_as_modified()
        return AgentResponse.done(self)

    async def ask_user_to_test(self, awaiting_bug_reproduction: bool = False, awaiting_user_test: bool = False):
        await self.send_message(
            "You can reproduce the bug like this:\n\n"
            + self.current_state.current_iteration["bug_reproduction_description"]
        )

        buttons = {}

        if self.current_state.run_command:
            await self.ui.send_run_command(self.current_state.run_command)

        if awaiting_user_test:
            buttons["yes"] = "Yes, the issue is fixed"
            buttons["no"] = "No"
            buttons["start_pair_programming"] = "Start Pair Programming"

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
            elif user_feedback.button == "start_pair_programming":
                self.next_state.current_iteration["status"] = IterationStatus.START_PAIR_PROGRAMMING
                self.next_state.flag_iterations_as_modified()
            else:
                awaiting_bug_reproduction = True

        if awaiting_bug_reproduction:
            # TODO how can we get FE and BE logs automatically?
            buttons["continue"] = "Continue"
            buttons["done"] = "Bug is fixed"
            backend_logs = await self.ask_question(
                "Please do exactly what you did in the last iteration, paste the BACKEND logs here and click CONTINUE.",
                buttons=buttons,
                default="continue",
                hint="Instructions for testing:\n\n"
                + self.current_state.current_iteration["bug_reproduction_description"],
            )

            if backend_logs.button == "done":
                self.next_state.complete_iteration()
            elif backend_logs.button == "start_pair_programming":
                self.next_state.current_iteration["status"] = IterationStatus.START_PAIR_PROGRAMMING
                self.next_state.flag_iterations_as_modified()
            else:
                frontend_logs = await self.ask_question(
                    "Please paste the FRONTEND logs here and click CONTINUE.",
                    buttons={"continue": "Continue", "done": "Bug is fixed"},
                    default="continue",
                    hint="Instructions for testing:\n\n"
                    + self.current_state.current_iteration["bug_reproduction_description"],
                )

                if frontend_logs.button == "done":
                    self.next_state.complete_iteration()
                else:
                    user_feedback = await self.ask_question(
                        "Do you want to add anything else to help Pythagora solve this bug?",
                        buttons={"continue": "Continue", "done": "Bug is fixed"},
                        default="continue",
                        hint="Instructions for testing:\n\n"
                        + self.current_state.current_iteration["bug_reproduction_description"],
                    )

                # TODO select only the logs that are new (with PYTHAGORA_DEBUGGING_LOG)
                self.next_state.current_iteration["bug_hunting_cycles"][-1]["backend_logs"] = backend_logs.text
                self.next_state.current_iteration["bug_hunting_cycles"][-1]["frontend_logs"] = frontend_logs.text
                self.next_state.current_iteration["bug_hunting_cycles"][-1]["user_feedback"] = user_feedback.text
                self.next_state.current_iteration["status"] = IterationStatus.HUNTING_FOR_BUG

        return AgentResponse.done(self)

    async def start_pair_programming(self):
        llm = self.get_llm(stream_output=True)
        convo = self.generate_iteration_convo_so_far(True)
        if len(convo.messages) > 1:
            convo.remove_last_x_messages(1)
        convo = convo.template("problem_explanation")
        await self.ui.start_important_stream()
        initial_explanation = await llm(convo, temperature=0.5)

        convo = convo.template("data_about_logs").require_schema(ImportantLogsForDebugging)

        data_about_logs = await llm(convo, parser=JSONParser(ImportantLogsForDebugging), temperature=0.5)

        await self.ui.send_data_about_logs(
            {
                "logs": [
                    {
                        "currentLog": d.currentOutput,
                        "expectedLog": d.expectedOutput,
                        "explanation": d.explanation,
                        "filePath": d.filePath,
                        "logCode": d.logCode,
                        "shouldBeDifferent": d.shouldBeDifferent,
                    }
                    for d in data_about_logs.logs
                ]
            }
        )

        while True:
            self.next_state.current_iteration["initial_explanation"] = initial_explanation
            next_step = await self.ask_question(
                "What do you want to do?",
                buttons={
                    "question": "I have a question",
                    "done": "I fixed the bug myself",
                    "tell_me_more": "Tell me more about the bug",
                    "solution_hint": "I think I know where the problem is",
                    "other": "Other",
                },
                buttons_only=True,
                default="continue",
                hint="Instructions for testing:\n\n"
                + self.current_state.current_iteration["bug_reproduction_description"],
            )

            await telemetry.trace_code_event(
                "pair-programming",
                {
                    "button": next_step.button,
                    "num_tasks": len(self.current_state.tasks),
                    "num_epics": len(self.current_state.epics),
                    "num_iterations": len(self.current_state.iterations),
                    "app_id": str(self.state_manager.project.id),
                    "app_name": self.state_manager.project.name,
                    "folder_name": self.state_manager.project.folder_name,
                },
            )

            # TODO: remove when Leon checks
            convo.remove_last_x_messages(2)

            if len(convo.messages) > 10:
                convo.trim(1, 2)

            # TODO: in the future improve with a separate conversation that parses the user info and goes into an appropriate if statement
            if next_step.button == "done":
                self.next_state.complete_iteration()
                break
            elif next_step.button == "question":
                user_response = await self.ask_question("Oh, cool, what would you like to know?")
                convo = convo.template("ask_a_question", question=user_response.text)
                await self.ui.start_important_stream()
                llm_answer = await llm(convo, temperature=0.5)
                await self.send_message(llm_answer)
            elif next_step.button == "tell_me_more":
                convo.template("tell_me_more")
                await self.ui.start_important_stream()
                response = await llm(convo, temperature=0.5)
                await self.send_message(response)
            elif next_step.button == "other":
                # this is the same as "question" - we want to keep an option for users to click to understand if we're missing something with other options
                user_response = await self.ask_question("Let me know what you think ...")
                convo = convo.template("ask_a_question", question=user_response.text)
                await self.ui.start_important_stream()
                llm_answer = await llm(convo, temperature=0.5)
                await self.send_message(llm_answer)
            elif next_step.button == "solution_hint":
                human_hint_label = "Amazing! How do you think we can solve this bug?"
                while True:
                    human_hint = await self.ask_question(human_hint_label)
                    convo = convo.template("instructions_from_human_hint", human_hint=human_hint.text)
                    await self.ui.start_important_stream()
                    llm = self.get_llm(CHECK_LOGS_AGENT_NAME, stream_output=True)
                    human_readable_instructions = await llm(convo, temperature=0.5)
                    human_approval = await self.ask_question(
                        "Can I implement this solution?", buttons={"yes": "Yes", "no": "No"}, buttons_only=True
                    )
                    llm = self.get_llm(stream_output=True)
                    if human_approval.button == "yes":
                        self.set_data_for_next_hunting_cycle(
                            human_readable_instructions, IterationStatus.AWAITING_BUG_FIX
                        )
                        self.next_state.flag_iterations_as_modified()
                        break
                    else:
                        human_hint_label = "Oh, my bad, what did I misunderstand?"
                break
            elif next_step.button == "tell_me_more":
                convo.template("tell_me_more")
                await self.ui.start_important_stream()
                response = await llm(convo, temperature=0.5)
                await self.send_message(response)
                continue

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
                backend_logs=hunting_cycle.get("backend_logs"),
                frontend_logs=hunting_cycle.get("frontend_logs"),
                fix_attempted=hunting_cycle.get("fix_attempted"),
                user_feedback=hunting_cycle.get("user_feedback"),
            )

        return convo

    def set_data_for_next_hunting_cycle(self, human_readable_instructions, new_status):
        self.next_state.current_iteration["description"] = human_readable_instructions
        self.next_state.current_iteration["bug_hunting_cycles"] += [
            {
                "human_readable_instructions": human_readable_instructions,
                "fix_attempted": any(
                    c["fix_attempted"] for c in self.current_state.current_iteration["bug_hunting_cycles"]
                ),
            }
        ]

        self.next_state.current_iteration["status"] = new_status

    async def continue_on(self, convo, button_value, user_response):
        llm = self.get_llm(stream_output=True)
        convo = convo.template("continue_on")
        continue_on = await llm(convo, temperature=0.5)
        return continue_on
