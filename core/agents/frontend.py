from uuid import uuid4

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import FRONTEND_AGENT_NAME
from core.llm.parser import DescriptiveCodeBlockParser
from core.log import get_logger
from core.telemetry import telemetry
from core.templates.base import NoOptions
from core.templates.registry import PROJECT_TEMPLATES

log = get_logger(__name__)


class Frontend(BaseAgent):
    agent_type = "frontend"
    display_name = "Frontend"

    async def run(self) -> AgentResponse:
        if not self.current_state.epics:
            finished = await self.init_frontend()
        elif not self.current_state.epics[0]["messages"]:
            await self.set_app_details()
            finished = await self.start_frontend()
        else:
            await self.set_app_details()
            finished = await self.iterate_frontend()

        return await self.end_frontend_iteration(finished)

    async def init_frontend(self) -> bool:
        """
        Builds frontend of the app.

        :return: AgentResponse.done(self)
        """
        description = await self.ask_question(
            "Please describe the app you want to build.",
            allow_empty=False,
            full_screen=True,
        )
        description = description.text.strip()

        await self.send_message("Setting up project...")

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

        await self.apply_template()

        return False

    async def start_frontend(self):
        """
        Starts the frontend of the app.
        """
        await self.send_message("Building frontend...")
        description = self.current_state.epics[0]["description"]

        llm = self.get_llm(FRONTEND_AGENT_NAME, stream_output=True)
        convo = AgentConvo(self).template(
            "build_frontend",
            description=description,
            user_feedback=None,
        )
        response = await llm(convo, parser=DescriptiveCodeBlockParser())

        await self.process_response(response, user_input=description)

        return False

    async def iterate_frontend(self) -> bool:
        """
        Iterates over the frontend.

        :return: True if the frontend is fully built, False otherwise.
        """

        answer = await self.ask_question(
            "Test the app and let us know if there are any issues or additional changes you want to make in the UI.",
            buttons={
                "yes": "I'm done building the UI",
                "copy_frontend_logs": "Copy Frontend Logs",
                "copy_backend_logs": "Copy Backend Logs",
            },
            default="yes",
            extra_info="restart_app",
        )

        if answer.button == "yes":
            answer = await self.ask_question(
                "Are you sure you're done building the UI and want to start building the backend functionality now?",
                buttons={
                    "yes": "Yes, let's build the backend.",
                    "no": "No, continue working on the UI.",
                },
                buttons_only=True,
                default="yes",
            )

            if answer.button == "yes":
                return True
            else:
                return False

        await self.send_message("Thinking how to implement this...")

        llm = self.get_llm(FRONTEND_AGENT_NAME, stream_output=True)
        convo = AgentConvo(self).template(
            "build_frontend",
            description=self.current_state.epics[0]["description"],
            user_feedback=answer.text,
        )
        response = await llm(convo, parser=DescriptiveCodeBlockParser())

        await self.process_response(response, user_input=answer.text)

        return False

    async def end_frontend_iteration(self, finished: bool) -> AgentResponse:
        """
        Ends the frontend iteration.

        :param finished: Whether the frontend is fully built.
        :return: AgentResponse.done(self)
        """
        if finished:
            # TODO Add question if user app is fully finished
            self.next_state.complete_epic()
            await telemetry.trace_code_event(
                "frontend-finished",
                {
                    "description": self.current_state.epics[0]["description"],
                    "messages": self.current_state.epics[0]["messages"],
                },
            )

        return AgentResponse.done(self)

    async def process_response(self, response: AgentResponse, user_input: str) -> AgentResponse:
        """
        Processes the response from the LLM.

        :param response: The response from the LLM.
        :param user_input: The user input.
        :return: AgentResponse.done(self)
        """
        self.next_state.epics[-1]["messages"].append(user_input)
        self.next_state.flag_epics_as_modified()

        for block in response.blocks:
            description = block.description.lower().strip()
            content = block.content.strip()

            if "file:" in description:
                # Extract file path from description - get everything after "file:"
                file_path = description[description.index("file:") + 5 :].strip()
                await self.send_message(f"Implementing file `{file_path}`...")
                await self.state_manager.save_file(file_path, content)

            elif description.endswith("command"):
                # Split multiple commands and execute them sequentially
                commands = content.strip().split("\n")
                for command in commands:
                    command = command.strip()
                    if command:
                        # Add "cd client" prefix if not already present
                        if not command.startswith("cd client"):
                            command = f"cd client && {command}"
                        await self.send_message(f"Running command: `{command}`...")
                        await self.process_manager.run_command(command)
            else:
                log.info(f"Unknown block description: {description}")

        return AgentResponse.done(self)

    async def apply_template(self):
        """
        Applies a template to the frontend.
        """
        template_name = "vite_react"
        template_class = PROJECT_TEMPLATES.get(template_name)
        if not template_class:
            log.error(f"Project template not found: {template_name}")
            return

        template = template_class(
            NoOptions(),
            self.state_manager,
            self.process_manager,
        )

        log.info(f"Applying project template: {template.name}")
        summary = await template.apply()

        self.next_state.relevant_files = template.relevant_files
        self.next_state.modified_files = {}
        return summary

    async def set_app_details(self):
        """
        Sets the app details.
        """
        command = "npm run start"
        app_link = "http://localhost:5173"

        self.next_state.run_command = command
        # todo store app link and send whenever we are sending run_command
        # self.next_state.app_link = app_link
        await self.ui.send_run_command(command)
        await self.ui.send_app_link(app_link)
