from typing import Optional

from pydantic import BaseModel, Field

from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import GET_RELEVANT_FILES_AGENT_NAME, TROUBLESHOOTER_BUG_REPORT
from core.llm.parser import JSONParser
from core.log import get_logger

log = get_logger(__name__)


class RelevantFiles(BaseModel):
    read_files: list[str] = Field(description="List of files you want to read.")
    add_files: list[str] = Field(description="List of files you want to add to the list of relevant files.")
    remove_files: list[str] = Field(description="List of files you want to remove from the list of relevant files.")
    done: bool = Field(description="Boolean flag to indicate that you are done selecting relevant files.")


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
        )
        llm_solution: str = await llm(convo)
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

        while not done and len(convo.messages) < 13:
            llm_response: RelevantFiles = await llm(convo, parser=JSONParser(RelevantFiles), temperature=0)

            # Check if there are files to add to the list
            if llm_response.add_files:
                # Add only the files from add_files that are not already in relevant_files
                relevant_files.update(file for file in llm_response.add_files if file not in relevant_files)

            # Check if there are files to remove from the list
            if llm_response.remove_files:
                # Remove files from relevant_files that are in remove_files
                relevant_files.difference_update(llm_response.remove_files)

            read_files = [file for file in self.current_state.files if file.path in llm_response.read_files]

            convo.remove_last_x_messages(1)
            convo.assistant(llm_response.original_response)
            convo.template("filter_files_loop", read_files=read_files, relevant_files=relevant_files).require_schema(
                RelevantFiles
            )
            done = llm_response.done

        existing_files = {file.path for file in self.current_state.files}
        relevant_files = [path for path in relevant_files if path in existing_files]
        self.next_state.relevant_files = relevant_files

        return AgentResponse.done(self)
