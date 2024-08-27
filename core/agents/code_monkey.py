from os.path import basename

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse, ResponseType
from core.config import CODE_MONKEY_AGENT_NAME, DESCRIBE_FILES_AGENT_NAME
from core.llm.parser import JSONParser, OptionalCodeBlockParser
from core.log import get_logger

log = get_logger(__name__)


class FileDescription(BaseModel):
    summary: str = Field(
        description="Detailed description summarized what the file is about, and what the major classes, functions, elements or other functionality is implemented."
    )
    references: list[str] = Field(
        description="List of references the file imports or includes (only files local to the project), where each element specifies the project-relative path of the referenced file, including the file extension."
    )


class CodeMonkey(BaseAgent):
    agent_type = "code-monkey"
    display_name = "Code Monkey"

    async def run(self) -> AgentResponse:
        if self.prev_response and self.prev_response.type == ResponseType.DESCRIBE_FILES:
            return await self.describe_files()
        else:
            return await self.implement_changes()

    async def implement_changes(self) -> AgentResponse:
        file_name = self.step["save_file"]["path"]

        current_file = await self.state_manager.get_file_by_path(file_name)
        file_content = current_file.content.content if current_file else ""

        task = self.current_state.current_task

        if self.prev_response and self.prev_response.type == ResponseType.CODE_REVIEW_FEEDBACK:
            attempt = self.prev_response.data["attempt"] + 1
            feedback = self.prev_response.data["feedback"]
            log.debug(f"Fixing file {file_name} after review feedback: {feedback} ({attempt}. attempt)")
            await self.send_message(f"Reworking changes I made to {file_name} ...")
        else:
            log.debug(f"Implementing file {file_name}")
            await self.send_message(f"{'Updating existing' if file_content else 'Creating new'} file {file_name} ...")
            self.next_state.action = (
                f'Update file "{basename(file_name)}"' if file_content else f'Create file "{basename(file_name)}"'
            )
            attempt = 1
            feedback = None

        iterations = self.current_state.iterations
        user_feedback = None
        user_feedback_qa = None
        llm = self.get_llm(CODE_MONKEY_AGENT_NAME)

        if "task_review_feedback" in task and task["task_review_feedback"]:
            instructions = task.get("task_review_feedback")
        elif iterations:
            last_iteration = iterations[-1]
            instructions = last_iteration.get("description")
            user_feedback = last_iteration.get("user_feedback")
            user_feedback_qa = last_iteration.get("user_feedback_qa")
        else:
            instructions = self.current_state.current_task["instructions"]

        convo = AgentConvo(self).template(
            "implement_changes",
            file_name=file_name,
            file_content=file_content,
            instructions=instructions,
            user_feedback=user_feedback,
            user_feedback_qa=user_feedback_qa,
        )
        if feedback:
            convo.assistant(f"```\n{self.prev_response.data['new_content']}\n```\n").template(
                "review_feedback",
                content=self.prev_response.data["approved_content"],
                original_content=file_content,
                rework_feedback=feedback,
            )

        response: str = await llm(convo, temperature=0, parser=OptionalCodeBlockParser())
        # FIXME: provide a counter here so that we don't have an endless loop here
        return AgentResponse.code_review(self, file_name, task["instructions"], file_content, response, attempt)

    async def describe_files(self) -> AgentResponse:
        llm = self.get_llm(DESCRIBE_FILES_AGENT_NAME)
        to_describe = {
            file.path: file.content.content for file in self.current_state.files if not file.meta.get("description")
        }

        for file in self.next_state.files:
            content = to_describe.get(file.path)
            if content is None:
                continue

            if content == "":
                file.meta = {
                    **file.meta,
                    "description": "Empty file",
                    "references": [],
                }
                continue

            log.debug(f"Describing file {file.path}")
            convo = (
                AgentConvo(self)
                .template(
                    "describe_file",
                    path=file.path,
                    content=content,
                )
                .require_schema(FileDescription)
            )
            llm_response: FileDescription = await llm(convo, parser=JSONParser(spec=FileDescription))

            file.meta = {
                **file.meta,
                "description": llm_response.summary,
                "references": llm_response.references,
            }
        return AgentResponse.done(self)
