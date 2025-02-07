import json
from difflib import unified_diff
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import GET_RELEVANT_FILES_AGENT_NAME, TASK_BREAKDOWN_AGENT_NAME, TROUBLESHOOTER_BUG_REPORT
from core.llm.parser import JSONParser
from core.log import get_logger
from core.ui.base import ProjectStage

log = get_logger(__name__)


class ReadFilesAction(BaseModel):
    read_files: Optional[List[str]] = Field(
        description="List of files you want to read. All listed files must be in the project."
    )


class AddFilesAction(BaseModel):
    add_files: Optional[List[str]] = Field(
        description="List of files you want to add to the list of relevant files. All listed files must be in the project. You must read files before adding them."
    )


class RemoveFilesAction(BaseModel):
    remove_files: Optional[List[str]] = Field(
        description="List of files you want to remove from the list of relevant files. All listed files must be in the relevant files list."
    )


class DoneBooleanAction(BaseModel):
    done: Optional[bool] = Field(description="Boolean flag to indicate that you are done creating breakdown.")


class RelevantFiles(BaseModel):
    action: Union[ReadFilesAction, AddFilesAction, RemoveFilesAction, DoneBooleanAction]


class Test(BaseModel):
    title: str = Field(description="Very short title of the test.")
    action: str = Field(description="More detailed description of what actions have to be taken to test the app.")
    result: str = Field(description="Expected result that verifies successful test.")


class TestSteps(BaseModel):
    steps: List[Test]


class ChatWithBreakdownMixin:
    """
    Provides a method to chat with the user and provide a breakdown of the conversation.
    """

    async def chat_with_breakdown(self, convo: AgentConvo, breakdown: str) -> AgentConvo:
        """
        Chat with the user and provide a breakdown of the conversation.

        :param convo: The conversation object.
        :param breakdown: The breakdown of the conversation.
        :return: The breakdown.
        """

        llm = self.get_llm(TASK_BREAKDOWN_AGENT_NAME, stream_output=True)
        while True:
            await self.ui.send_project_stage(
                {
                    "stage": ProjectStage.BREAKDOWN_CHAT,
                    "agent": self.agent_type,
                }
            )

            chat = await self.ask_question(
                "Are you happy with the breakdown? Now is a good time to ask questions or suggest changes.",
                buttons={"yes": "Yes, looks good!"},
                default="yes",
                verbose=False,
            )
            if chat.button == "yes":
                break

            if len(convo.messages) > 11:
                convo.trim(3, 2)

            convo.user(chat.text)
            breakdown: str = await llm(convo)
            convo.assistant(breakdown)

        return breakdown


class IterationPromptMixin:
    """
    Provides a method to find a solution to a problem based on user feedback.

    Used by ProblemSolver and Troubleshooter agents.
    """

    async def find_solution(
        self,
        user_feedback: str,
        *,
        user_feedback_qa: Optional[list[str]] = None,
        next_solution_to_try: Optional[str] = None,
        bug_hunting_cycles: Optional[dict] = None,
    ) -> str:
        """
        Generate a new solution for the problem the user reported.

        :param user_feedback: User feedback about the problem.
        :param user_feedback_qa: Additional q/a about the problem provided by the user (optional).
        :param next_solution_to_try: Hint from ProblemSolver on which solution to try (optional).
        :param bug_hunting_cycles: Data about logs that need to be added to the code (optional).
        :return: The generated solution to the problem.
        """
        llm = self.get_llm(TROUBLESHOOTER_BUG_REPORT, stream_output=True)
        convo = AgentConvo(self).template(
            "iteration",
            user_feedback=user_feedback,
            user_feedback_qa=user_feedback_qa,
            next_solution_to_try=next_solution_to_try,
            bug_hunting_cycles=bug_hunting_cycles,
            test_instructions=json.loads(self.current_state.current_task.get("test_instructions") or "[]"),
        )
        llm_solution: str = await llm(convo)

        llm_solution = await self.chat_with_breakdown(convo, llm_solution)

        return llm_solution


class RelevantFilesMixin:
    """
    Provides a method to get relevant files for the current task.
    """

    async def get_relevant_files(
        self, user_feedback: Optional[str] = None, solution_description: Optional[str] = None
    ) -> AgentResponse:
        log.debug("Getting relevant files for the current task")
        done = False
        relevant_files = set()
        llm = self.get_llm(GET_RELEVANT_FILES_AGENT_NAME)
        convo = (
            AgentConvo(self)
            .template(
                "filter_files",
                user_feedback=user_feedback,
                solution_description=solution_description,
                relevant_files=relevant_files,
            )
            .require_schema(RelevantFiles)
        )

        while not done and len(convo.messages) < 23:
            llm_response: RelevantFiles = await llm(convo, parser=JSONParser(RelevantFiles), temperature=0)
            action = llm_response.action
            if action is None:
                convo.remove_last_x_messages(2)
                continue

            # Check if there are files to add to the list
            if getattr(action, "add_files", None):
                # Add only the files from add_files that are not already in relevant_files
                relevant_files.update(file for file in action.add_files if file not in relevant_files)

            # Check if there are files to remove from the list
            if getattr(action, "remove_files", None):
                # Remove files from relevant_files that are in remove_files
                relevant_files.difference_update(action.remove_files)

            read_files = [
                file for file in self.current_state.files if file.path in (getattr(action, "read_files", []) or [])
            ]

            convo.remove_last_x_messages(1)
            convo.assistant(llm_response.original_response)
            convo.template("filter_files_loop", read_files=read_files, relevant_files=relevant_files).require_schema(
                RelevantFiles
            )
            done = getattr(action, "done", False)

        existing_files = {file.path for file in self.current_state.files}
        relevant_files = [path for path in relevant_files if path in existing_files]
        self.current_state.relevant_files = relevant_files
        self.next_state.relevant_files = relevant_files

        return AgentResponse.done(self)


class FileDiffMixin:
    """
    Provides a method to generate a diff between two files.
    """

    def get_line_changes(self, old_content: str, new_content: str) -> tuple[int, int]:
        """
        Get the number of added and deleted lines between two files.

        This uses Python difflib to produce a unified diff, then counts
        the number of added and deleted lines.

        :param old_content: old file content
        :param new_content: new file content
        :return: a tuple (added_lines, deleted_lines)
        """

        from_lines = old_content.splitlines(keepends=True)
        to_lines = new_content.splitlines(keepends=True)

        diff_gen = unified_diff(from_lines, to_lines)

        added_lines = 0
        deleted_lines = 0

        for line in diff_gen:
            if line.startswith("+") and not line.startswith("+++"):  # Exclude the file headers
                added_lines += 1
            elif line.startswith("-") and not line.startswith("---"):  # Exclude the file headers
                deleted_lines += 1

        return added_lines, deleted_lines
