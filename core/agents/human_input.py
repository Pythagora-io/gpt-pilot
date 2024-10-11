from core.agents.base import BaseAgent
from core.agents.response import AgentResponse, ResponseType


class HumanInput(BaseAgent):
    agent_type = "human-input"
    display_name = "Human Input"

    async def run(self) -> AgentResponse:
        if self.prev_response and self.prev_response.type == ResponseType.INPUT_REQUIRED:
            return await self.input_required(self.prev_response.data.get("files", []))

        return await self.human_intervention(self.step)

    async def human_intervention(self, step) -> AgentResponse:
        description = step["human_intervention_description"]

        await self.ask_question(
            f"I need human intervention: {description}",
            buttons={"continue": "Continue"},
            default="continue",
            buttons_only=True,
        )
        self.next_state.complete_step("human_intervention")
        return AgentResponse.done(self)

    async def input_required(self, files: list[dict]) -> AgentResponse:
        for item in files:
            file = item["file"]
            line = item["line"]

            # FIXME: this is an ugly hack, we shouldn't need to know how to get to VFS and
            # anyways the full path is only available for local vfs, so this is doubly wrong;
            # instead, we should just send the relative path to the extension and it should
            # figure out where its local files are and how to open it.
            full_path = self.state_manager.file_system.get_full_path(file)

            await self.send_message(f"Input required on {file}:{line}")
            await self.ui.open_editor(full_path, line)
            await self.ask_question(
                f"Please open {file} and modify line {line} according to the instructions.",
                buttons={"continue": "Continue"},
                default="continue",
                buttons_only=True,
            )
        return AgentResponse.done(self)
