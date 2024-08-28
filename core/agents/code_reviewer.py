import re
from difflib import unified_diff
from enum import Enum

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.llm.parser import JSONParser
from core.log import get_logger

log = get_logger(__name__)


# Constant for indicating missing new line at the end of a file in a unified diff
NO_EOL = "\\ No newline at end of file"

# Regular expression pattern for matching hunk headers
PATCH_HEADER_PATTERN = re.compile(r"^@@ -(\d+),?(\d+)? \+(\d+),?(\d+)? @@")

# Maximum number of attempts to ask for review if it can't be parsed
MAX_REVIEW_RETRIES = 2

# Maximum number of code implementation attempts after which we accept the changes unconditionaly
MAX_CODING_ATTEMPTS = 3


class Decision(str, Enum):
    APPLY = "apply"
    IGNORE = "ignore"
    REWORK = "rework"


class Hunk(BaseModel):
    number: int = Field(description="Index of the hunk in the diff. Starts from 1.")
    reason: str = Field(description="Reason for applying or ignoring this hunk, or for asking for it to be reworked.")
    decision: Decision = Field(description="Whether to apply this hunk, rework, or ignore it.")


class ReviewChanges(BaseModel):
    hunks: list[Hunk]
    review_notes: str = Field(description="Additional review notes (optional, can be empty).")


class CodeReviewer(BaseAgent):
    agent_type = "code-reviewer"
    display_name = "Code Reviewer"

    async def run(self) -> AgentResponse:
        if (
            not self.prev_response.data["old_content"]
            or self.prev_response.data["new_content"] == self.prev_response.data["old_content"]
            or self.prev_response.data["attempt"] >= MAX_CODING_ATTEMPTS
        ):
            # we always auto-accept new files and unchanged files, or if we've tried too many times
            return await self.accept_changes(self.prev_response.data["path"], self.prev_response.data["new_content"])

        approved_content, feedback = await self.review_change(
            self.prev_response.data["path"],
            self.prev_response.data["instructions"],
            self.prev_response.data["old_content"],
            self.prev_response.data["new_content"],
        )
        if feedback:
            return AgentResponse.code_review_feedback(
                self,
                new_content=self.prev_response.data["new_content"],
                approved_content=approved_content,
                feedback=feedback,
                attempt=self.prev_response.data["attempt"],
            )
        else:
            return await self.accept_changes(self.prev_response.data["path"], approved_content)

    async def accept_changes(self, path: str, content: str) -> AgentResponse:
        await self.state_manager.save_file(path, content)
        self.next_state.complete_step()

        input_required = self.state_manager.get_input_required(content)
        if input_required:
            return AgentResponse.input_required(
                self,
                [{"file": path, "line": line} for line in input_required],
            )
        else:
            return AgentResponse.done(self)

    def _get_task_convo(self) -> AgentConvo:
        # FIXME: Current prompts reuse conversation from the developer so we have to resort to this
        task = self.current_state.current_task
        current_task_index = self.current_state.tasks.index(task)

        convo = AgentConvo(self).template(
            "breakdown",
            task=task,
            iteration=None,
            current_task_index=current_task_index,
        )
        # TODO: We currently show last iteration to the code monkey; we might need to show the task
        # breakdown and all the iterations instead? To think about when refactoring prompts
        if self.current_state.iterations:
            convo.assistant(self.current_state.iterations[-1]["description"])
        else:
            convo.assistant(self.current_state.current_task["instructions"])
        return convo

    async def review_change(
        self, file_name: str, instructions: str, old_content: str, new_content: str
    ) -> tuple[str, str]:
        """
        Review changes that were applied to the file.

        This asks the LLM to act as a PR reviewer and for each part (hunk) of the
        diff, decide if it should be applied (kept) or ignored (removed from the PR).

        :param file_name: name of the file being modified
        :param instructions: instructions for the reviewer
        :param old_content: old file content
        :param new_content: new file content (with proposed changes)
        :return: tuple with file content update with approved changes, and review feedback

        Diff hunk explanation: https://www.gnu.org/software/diffutils/manual/html_node/Hunks.html
        """

        hunks = self.get_diff_hunks(file_name, old_content, new_content)

        llm = self.get_llm()
        convo = (
            self._get_task_convo()
            .template(
                "review_changes",
                instructions=instructions,
                file_name=file_name,
                old_content=old_content,
                hunks=hunks,
            )
            .require_schema(ReviewChanges)
        )
        llm_response: ReviewChanges = await llm(convo, temperature=0, parser=JSONParser(ReviewChanges))

        for i in range(MAX_REVIEW_RETRIES):
            reasons = {}
            ids_to_apply = set()
            ids_to_ignore = set()
            ids_to_rework = set()
            for hunk in llm_response.hunks:
                reasons[hunk.number - 1] = hunk.reason
                if hunk.decision == "apply":
                    ids_to_apply.add(hunk.number - 1)
                elif hunk.decision == "ignore":
                    ids_to_ignore.add(hunk.number - 1)
                elif hunk.decision == "rework":
                    ids_to_rework.add(hunk.number - 1)

            n_hunks = len(hunks)
            n_review_hunks = len(reasons)
            if n_review_hunks == n_hunks:
                break
            elif n_review_hunks < n_hunks:
                error = "Not all hunks have been reviewed. Please review all hunks and add 'apply', 'ignore' or 'rework' decision for each."
            elif n_review_hunks > n_hunks:
                error = f"Your review contains more hunks ({n_review_hunks}) than in the original diff ({n_hunks}). Note that one hunk may have multiple changed lines."

            # Max two retries; if the reviewer still hasn't reviewed all hunks, we'll just use the entire new content
            convo.assistant(llm_response.model_dump_json()).user(error)
            llm_response = await llm(convo, parser=JSONParser(ReviewChanges))
        else:
            return new_content, None

        hunks_to_apply = [h for i, h in enumerate(hunks) if i in ids_to_apply]
        diff_log = f"--- {file_name}\n+++ {file_name}\n" + "\n".join(hunks_to_apply)

        hunks_to_rework = [(i, h) for i, h in enumerate(hunks) if i in ids_to_rework]
        review_log = (
            "\n\n".join([f"## Change\n```{hunk}```\nReviewer feedback:\n{reasons[i]}" for (i, hunk) in hunks_to_rework])
            + "\n\nReview notes:\n"
            + llm_response.review_notes
        )

        if len(hunks_to_apply) == len(hunks):
            # await self.send_message("Applying entire change")
            log.info(f"Applying entire change to {file_name}")
            return new_content, None

        elif len(hunks_to_apply) == 0:
            if hunks_to_rework:
                # await self.send_message(
                #     f"Requesting rework for {len(hunks_to_rework)} changes with reason: {llm_response.review_notes}"
                # )
                log.info(f"Requesting rework for {len(hunks_to_rework)} changes to {file_name} (0 hunks to apply)")
                return old_content, review_log
            else:
                # If everything can be safely ignored, it's probably because the files already implement the changes
                # from previous tasks (which can happen often). Insisting on a change here is likely to cause problems.
                # await self.send_message(f"Rejecting entire change with reason: {llm_response.review_notes}")
                log.info(f"Rejecting entire change to {file_name} with reason: {llm_response.review_notes}")
                return old_content, None

        log.debug(f"Applying code change to {file_name}:\n{diff_log}")
        new_content = self.apply_diff(file_name, old_content, hunks_to_apply, new_content)
        if hunks_to_rework:
            log.info(f"Requesting further rework for {len(hunks_to_rework)} changes to {file_name}")
            return new_content, review_log
        else:
            return new_content, None

    @staticmethod
    def get_diff_hunks(file_name: str, old_content: str, new_content: str) -> list[str]:
        """
        Get the diff between two files.

        This uses Python difflib to produce an unified diff, then splits
        it into hunks that will be separately reviewed by the reviewer.

        :param file_name: name of the file being modified
        :param old_content: old file content
        :param new_content: new file content
        :return: change hunks from the unified diff
        """
        from_name = "old_" + file_name
        to_name = "to_" + file_name
        from_lines = old_content.splitlines(keepends=True)
        to_lines = new_content.splitlines(keepends=True)
        diff_gen = unified_diff(from_lines, to_lines, fromfile=from_name, tofile=to_name)
        diff_txt = "".join(diff_gen)

        hunks = re.split(r"\n@@", diff_txt, re.MULTILINE)
        result = []
        for i, h in enumerate(hunks):
            # Skip the prologue (file names)
            if i == 0:
                continue
            txt = h.splitlines()
            txt[0] = "@@" + txt[0]
            result.append("\n".join(txt))
        return result

    def apply_diff(self, file_name: str, old_content: str, hunks: list[str], fallback: str):
        """
        Apply the diff to the original file content.

        This uses the internal `_apply_patch` method to apply the
        approved diff hunks to the original file content.

        If patch apply fails, the fallback is the full new file content
        with all the changes applied (as if the reviewer approved everythng).

        :param file_name: name of the file being modified
        :param old_content: old file content
        :param hunks: change hunks from the unified diff
        :param fallback: proposed new file content (with all the changes applied)
        """
        diff = (
            "\n".join(
                [
                    f"--- {file_name}",
                    f"+++ {file_name}",
                ]
                + hunks
            )
            + "\n"
        )
        try:
            fixed_content = self._apply_patch(old_content, diff)
        except Exception as e:
            # This should never happen but if it does, just use the new version from
            # the LLM and hope for the best
            print(f"Error applying diff: {e}; hoping all changes are valid")
            return fallback

        return fixed_content

    # Adapted from https://gist.github.com/noporpoise/16e731849eb1231e86d78f9dfeca3abc (Public Domain)
    @staticmethod
    def _apply_patch(original: str, patch: str, revert: bool = False):
        """
        Apply a patch to a string to recover a newer version of the string.

        :param original: The original string.
        :param patch: The patch to apply.
        :param revert: If True, treat the original string as the newer version and recover the older string.
        :return: The updated string after applying the patch.
        """
        original_lines = original.splitlines(True)
        patch_lines = patch.splitlines(True)

        updated_text = ""
        index_original = start_line = 0

        # Choose which group of the regex to use based on the revert flag
        match_index, line_sign = (1, "+") if not revert else (3, "-")

        # Skip header lines of the patch
        while index_original < len(patch_lines) and patch_lines[index_original].startswith(("---", "+++")):
            index_original += 1

        while index_original < len(patch_lines):
            match = PATCH_HEADER_PATTERN.match(patch_lines[index_original])
            if not match:
                raise Exception("Bad patch -- regex mismatch [line " + str(index_original) + "]")

            line_number = int(match.group(match_index)) - 1 + (match.group(match_index + 1) == "0")

            if start_line > line_number or line_number > len(original_lines):
                raise Exception("Bad patch -- bad line number [line " + str(index_original) + "]")

            updated_text += "".join(original_lines[start_line:line_number])
            start_line = line_number
            index_original += 1

            while index_original < len(patch_lines) and patch_lines[index_original][0] != "@":
                if index_original + 1 < len(patch_lines) and patch_lines[index_original + 1][0] == "\\":
                    line_content = patch_lines[index_original][:-1]
                    index_original += 2
                else:
                    line_content = patch_lines[index_original]
                    index_original += 1

                if line_content:
                    if line_content[0] == line_sign or line_content[0] == " ":
                        updated_text += line_content[1:]
                    start_line += line_content[0] != line_sign

        updated_text += "".join(original_lines[start_line:])
        return updated_text
