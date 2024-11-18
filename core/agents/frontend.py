from uuid import uuid4

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import FRONTEND_AGENT_NAME
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)


class Frontend(BaseAgent):
    agent_type = "frontend"
    display_name = "Frontend"

    async def run(self) -> AgentResponse:
        if not self.current_state.epics:
            finished = await self.init_frontend()
        else:
            finished = await self.iterate_frontend()

        return await self.end_frontend_iteration(finished)

    async def init_frontend(self) -> bool:
        """
        Builds frontend of the app.

        :return: AgentResponse.done(self)
        """
        description = await self.ask_question(
            "Give short description of the app UI.",
            allow_empty=False,
            full_screen=True,
        )

        self.next_state.epics = [
            {
                "id": uuid4().hex,
                "name": "Build frontend",
                "source": "frontend",
                "description": description,
                "messages": [],
                "summary": None,
                "completed": False,
            }
        ]

        llm = self.get_llm(FRONTEND_AGENT_NAME)
        convo = AgentConvo(self).template(
            "build_frontend",
            description=description,
        )
        response = await llm(convo)

        return response

    async def iterate_frontend(self) -> bool:
        """
        Iterates over the frontend.

        :return: True if the frontend is fully built, False otherwise.
        """

        answer = self.ask_question(
            "Are you finished making UI changes?",
            buttons={
                "yes": "Yes, let's build the app!",
            },
            default="continue",
            initial_text="I would like to add /admin page...",
        )

        if answer.button == "yes":
            return True

        llm = self.get_llm(FRONTEND_AGENT_NAME)
        convo = (
            AgentConvo(self)
            .template(
                "iterate_frontend",
            )
            .assistant("")
            .template("parse_task")
        )
        response = await llm(convo)

        return response

    async def end_frontend_iteration(self, finished: bool) -> AgentResponse:
        """
        Ends the frontend iteration.

        :param finished: Whether the frontend is fully built.
        :return: AgentResponse.done(self)
        """
        if finished:
            self.next_state.complete_epic()
            await telemetry.trace_code_event("frontend-finished")

        return AgentResponse.done(self)
