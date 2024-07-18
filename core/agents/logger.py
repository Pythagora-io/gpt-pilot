from uuid import uuid4

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.mixins import TaskSteps
from core.agents.response import AgentResponse
from core.db.models.project_state import IterationStatus
from core.llm.parser import JSONParser
from core.log import get_logger

log = get_logger(__name__)


class Logger(BaseAgent):
    agent_type = "logger"
    display_name = "Logger Agent"

    async def run(self) -> AgentResponse:
        current_iteration = self.current_state.current_iteration

        if current_iteration["status"] == IterationStatus.CHECK_LOGS:
            return await self.check_logs()
        elif current_iteration["status"] == IterationStatus.AWAITING_TEST:
            return await self.ask_user_to_test()

    async def check_logs(self):
        llm = self.get_llm()
        convo = AgentConvo(self).template("check_if_logs_needed").require_schema(TaskSteps)
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        if response.lower() == "done":
            # if no need for logs, implement iteration same as before
            self.next_state.current_iteration["status"] = IterationStatus.IMPLEMENT
            self.next_state.flag_iterations_as_modified()
            return AgentResponse.done(self)

        # if logs are needed, add logging steps
        convo = AgentConvo(self).template("generate_steps").require_schema(TaskSteps)
        response: TaskSteps = await llm(convo, parser=JSONParser(TaskSteps), temperature=0)

        self.next_state.steps += [
            {
                "id": uuid4().hex,
                "completed": False,
                "source": "logger",
                "iteration_index": len(self.current_state.iterations),
                **step.model_dump(),
            }
            for step in response.steps
        ]

        self.next_state.current_iteration["status"] = IterationStatus.AWAITING_TEST
        self.next_state.flag_iterations_as_modified()
        return AgentResponse.done(self)

    async def ask_user_to_test(self):
        await self.ask_question(
            "Please test the changes and let me know if everything is working.",
            buttons={"continue": "Continue"},
            buttons_only=True,
            default="continue",
        )

        # todo change status of iteration and flag iteration as modified
        # self.next_state.current_iteration["logs_data"] = answer
        # self.next_state.current_iteration["status"] = IterationStatus.IMPLEMENT
        # self.next_state.flag_iterations_as_modified()
        return AgentResponse.done(self)
