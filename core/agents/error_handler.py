from uuid import uuid4

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.db.models.project_state import IterationStatus
from core.log import get_logger

log = get_logger(__name__)


class ErrorHandler(BaseAgent):
    """
    Error handler agent.

    Error handler is responsible for handling errors returned by other agents. If it's possible
    to recover from the error, it should do it (which may include updating the "next" state) and
    return DONE. Otherwise it should return EXIT to tell Orchestrator to quit the application.
    """

    agent_type = "error-handler"
    display_name = "Error Handler"

    async def run(self) -> AgentResponse:
        from core.agents.executor import Executor
        from core.agents.spec_writer import SpecWriter

        error = self.prev_response
        if error is None:
            log.warning("ErrorHandler called without a previous error", stack_info=True)
            return AgentResponse.done(self)

        log.error(
            f"Agent {error.agent.display_name} returned error response: {error.type}",
            extra={"data": error.data},
        )

        if isinstance(error.agent, SpecWriter):
            # If SpecWriter wasn't able to get the project description, there's nothing for
            # us to do.
            return AgentResponse.exit(self)

        if isinstance(error.agent, Executor):
            return await self.handle_command_error(
                error.data.get("message", "Unknown error"), error.data.get("details", {})
            )

        log.error(
            f"Unhandled error response from agent {error.agent.display_name}",
            extra={"data": error.data},
        )
        return AgentResponse.exit(self)

    async def handle_command_error(self, message: str, details: dict) -> AgentResponse:
        """
        Handle an error returned by Executor agent.

        Error message must be the analyis of the command execution, and the details must contain:
        * cmd - command that was executed
        * timeout - timeout for the command if any (or None if no timeout was used)
        * status_code - exit code for the command (or None if the command timed out)
        * stdout - standard output of the command
        * stderr - standard error of the command

        :return: AgentResponse
        """
        cmd = details.get("cmd")
        timeout = details.get("timeout")
        status_code = details.get("status_code")
        stdout = details.get("stdout", "")
        stderr = details.get("stderr", "")

        if not message:
            raise ValueError("No error message provided in command error response")
        if not cmd:
            raise ValueError("No command provided in command error response details")

        confirm = await self.ask_question(
            "Can I debug why this command failed?",
            buttons={"yes": "Yes", "no": "No"},
            default="yes",
            buttons_only=True,
        )
        if confirm.cancelled or confirm.button == "no":
            log.info("Skipping command error debug (requested by user)")
            return AgentResponse.done(self)

        llm = self.get_llm(stream_output=True)
        convo = AgentConvo(self).template(
            "debug",
            task_steps=self.current_state.steps,
            current_task=self.current_state.current_task,
            # FIXME: can this break?
            step_index=self.current_state.steps.index(self.current_state.current_step),
            cmd=cmd,
            timeout=timeout,
            stdout=stdout,
            stderr=stderr,
            status_code=status_code,
            # fixme: everything above copypasted from Executor
            analysis=message,
        )
        llm_response: str = await llm(convo)

        # TODO: duplicate from Troubleshooter, maybe extract to a ProjectState method?
        self.next_state.iterations = self.current_state.iterations + [
            {
                "id": uuid4().hex,
                "user_feedback": f"Error running command: {cmd}",
                "user_feedback_qa": None,
                "description": llm_response,
                "alternative_solutions": [],
                "attempts": 1,
                "status": IterationStatus.IMPLEMENT_SOLUTION,
                "bug_hunting_cycles": [],
            }
        ]
        # TODO: maybe have ProjectState.finished_steps as well? would make the debug/ran_command prompts nicer too
        self.next_state.steps = [s for s in self.current_state.steps if s.get("completed") is True]
        # No need to call complete_step() here as we've just removed the steps so that Developer can break down the iteration
        return AgentResponse.done(self)
