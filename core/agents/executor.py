from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.llm.parser import JSONParser
from core.log import get_logger
from core.proc.exec_log import ExecLog
from core.proc.process_manager import ProcessManager
from core.state.state_manager import StateManager
from core.ui.base import AgentSource, UIBase, UISource

log = get_logger(__name__)

CMD_OUTPUT_SOURCE_NAME = "Command output"
CMD_OUTPUT_SOURCE_TYPE = "cli-output"


class CommandResult(BaseModel):
    """
    Analysis of the command run and decision on the next steps.
    """

    analysis: str = Field(
        description="Analysis of the command output (stdout, stderr) and exit code, in context of the current task"
    )
    success: bool = Field(
        description="True if the command should be treated as successful and the task should continue, false if the command unexpectedly failed and we should debug the issue"
    )


class Executor(BaseAgent):
    agent_type = "executor"
    display_name = "Executor"

    def __init__(
        self,
        state_manager: StateManager,
        ui: UIBase,
    ):
        """
        Create a new Executor agent
        """
        self.ui_source = AgentSource(self.display_name, self.agent_type)
        self.cmd_ui_source = UISource(CMD_OUTPUT_SOURCE_NAME, CMD_OUTPUT_SOURCE_TYPE)

        self.ui = ui
        self.state_manager = state_manager
        self.process_manager = ProcessManager(
            root_dir=state_manager.get_full_project_root(),
            output_handler=self.output_handler,
            exit_handler=self.exit_handler,
        )

    def for_step(self, step):
        # FIXME: not needed, refactor to use self.current_state.current_step
        # in general, passing current step is not needed
        self.step = step
        return self

    async def output_handler(self, out, err):
        await self.ui.send_stream_chunk(out, source=self.cmd_ui_source)
        await self.ui.send_stream_chunk(err, source=self.cmd_ui_source)

    async def exit_handler(self, process):
        pass

    async def run(self) -> AgentResponse:
        if not self.step:
            raise ValueError("No current step set (probably an Orchestrator bug)")

        options = self.step["command"]
        cmd = options["command"]
        cmd_name = cmd[:30] + "..." if len(cmd) > 33 else cmd
        timeout = options.get("timeout")

        if timeout:
            q = f"Can I run command: {cmd} with {timeout}s timeout?"
        else:
            q = f"Can I run command: {cmd}?"

        confirm = await self.ask_question(
            q,
            buttons={"yes": "Yes", "no": "No"},
            default="yes",
            buttons_only=False,
            initial_text=cmd,
            extra_info="remove_button_yes",
        )
        if confirm.button == "no":
            log.info(f"Skipping command execution of `{cmd}` (requested by user)")
            await self.send_message(f"Skipping command {cmd}")
            self.complete()
            self.next_state.action = f'Skip "{cmd_name}"'
            return AgentResponse.done(self)

        if confirm.button != "yes":
            cmd = confirm.text

        started_at = datetime.now(timezone.utc)

        log.info(f"Running command `{cmd}` with timeout {timeout}s")
        status_code, stdout, stderr = await self.process_manager.run_command(cmd, timeout=timeout)

        llm_response = await self.check_command_output(cmd, timeout, stdout, stderr, status_code)

        duration = (datetime.now(timezone.utc) - started_at).total_seconds()

        self.complete()
        self.next_state.action = f'Run "{cmd_name}"'

        exec_log = ExecLog(
            started_at=started_at,
            duration=duration,
            cmd=cmd,
            cwd=".",
            env={},
            timeout=timeout,
            status_code=status_code,
            stdout=stdout,
            stderr=stderr,
            analysis=llm_response.analysis,
            success=llm_response.success,
        )
        await self.state_manager.log_command_run(exec_log)

        # FIXME: ErrorHandler isn't debugged with BugHunter - we should move all commands to run before testing and debug them with BugHunter
        if True or llm_response.success:
            return AgentResponse.done(self)

        return AgentResponse.error(
            self,
            llm_response.analysis,
            {
                "cmd": cmd,
                "timeout": timeout,
                "stdout": stdout,
                "stderr": stderr,
                "status_code": status_code,
            },
        )

    async def check_command_output(
        self, cmd: str, timeout: Optional[int], stdout: str, stderr: str, status_code: int
    ) -> CommandResult:
        llm = self.get_llm()
        convo = (
            AgentConvo(self)
            .template(
                "ran_command",
                task_steps=self.current_state.steps,
                current_task=self.current_state.current_task,
                # FIXME: can step ever happen *not* to be in current steps?
                step_index=self.current_state.steps.index(self.step),
                cmd=cmd,
                timeout=timeout,
                stdout=stdout,
                stderr=stderr,
                status_code=status_code,
            )
            .require_schema(CommandResult)
        )
        return await llm(convo, parser=JSONParser(spec=CommandResult), temperature=0)

    def complete(self):
        """
        Mark the step as complete.

        Note that this marks the step complete in the next state. If there's an error,
        the state won't get committed and the error handler will have access to the
        current state, where this step is still unfinished.

        This is intentional, so that the error handler can decide what to do with the
        information we give it.
        """
        self.step = None
        self.next_state.complete_step("command")
