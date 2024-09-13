import random
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import GET_RELEVANT_FILES_AGENT_NAME, TROUBLESHOOTER_BUG_REPORT
from core.config.magic_words import THINKING_LOGS
from core.llm.parser import JSONParser
from core.log import get_logger

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
            action = llm_response.action

            # Check if there are files to add to the list
            if getattr(action, "add_files", None):
                # Add only the files from add_files that are not already in relevant_files
                relevant_files.update(file for file in action.add_files if file not in relevant_files)

            # Check if there are files to remove from the list
            if getattr(action, "remove_files", None):
                # Remove files from relevant_files that are in remove_files
                relevant_files.difference_update(action.remove_files)

            read_files = [file for file in self.current_state.files if file.path in getattr(action, "read_files", [])]

            convo.remove_last_x_messages(1)
            convo.assistant(llm_response.original_response)
            convo.template("filter_files_loop", read_files=read_files, relevant_files=relevant_files).require_schema(
                RelevantFiles
            )
            done = getattr(action, "done", False)

        existing_files = {file.path for file in self.current_state.files}
        relevant_files = [path for path in relevant_files if path in existing_files]
        self.next_state.relevant_files = relevant_files

        return AgentResponse.done(self)


class ActionsConversationMixin:
    """
    Provides a method to loop in conversation until done.
    """

    async def actions_conversation(
        self,
        data: any,
        original_prompt: str,
        loop_prompt: str,
        schema,
        llm_config,
        temperature: Optional[float] = 0.5,
        max_convo_length: Optional[int] = 20,
        stream_llm_output: Optional[bool] = False,
    ) -> tuple[AgentConvo, any]:
        """
        Loop in conversation until done.

        :param data: The initial data to pass into the conversation.
        :param original_prompt: The prompt template name for the initial request.
        :param loop_prompt: The prompt template name for the looped requests.
        :param schema: The schema class to enforce the structure of the LLM response.
        :param llm_config: The LLM configuration to use for the conversation.
        :param temperature: The temperature to use for the LLM response.
        :param max_convo_length: The maximum number of messages to allow in the conversation.

        :return: A tuple of the conversation and the final aggregated data.
        """
        llm = self.get_llm(llm_config, stream_output=stream_llm_output)
        convo = (
            AgentConvo(self)
            .template(
                original_prompt,
                **data,
            )
            .require_schema(schema)
        )
        response = await llm(convo, parser=JSONParser(schema), temperature=temperature)
        convo.remove_last_x_messages(1)
        convo.assistant(response.original_response)

        # Initialize loop_data to store the cumulative data from the loop
        loop_data = {
            attr: getattr(response.action, attr, None) for attr in dir(response.action) if not attr.startswith("_")
        }
        loop_data["read_files"] = getattr(response.action, "read_files", [])
        done = getattr(response.action, "done", False)

        # Keep working on the task until `done` or we reach 20 messages in convo.
        while not done and len(convo.messages) < max_convo_length:
            await self.send_message(random.choice(THINKING_LOGS))

            convo.template(
                loop_prompt,
                **loop_data,
            ).require_schema(schema)
            response = await llm(convo, parser=JSONParser(schema), temperature=temperature)
            convo.remove_last_x_messages(1)
            convo.assistant(response.original_response)

            # Update loop_data with new information, replacing everything except for 'read_files'
            for attr in dir(response.action):
                if not attr.startswith("_"):
                    current_value = getattr(response.action, attr, None)
                    if attr == "read_files" and current_value:
                        loop_data[attr].extend(item for item in current_value if item not in loop_data[attr])
                    else:
                        loop_data[attr] = current_value

            done = getattr(response.action, "done", False)

        return convo, loop_data
