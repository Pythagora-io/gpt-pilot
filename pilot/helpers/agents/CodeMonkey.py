import os.path
import re
from typing import Optional
from traceback import format_exc
from difflib import unified_diff

from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from helpers.files import get_file_contents
from const.function_calls import GET_FILE_TO_MODIFY, REVIEW_CHANGES
from logger.logger import logger

from utils.exit import trace_code_event
from utils.telemetry import telemetry

# Constant for indicating missing new line at the end of a file in a unified diff
NO_EOL = "\ No newline at end of file"

# Regular expression pattern for matching hunk headers
PATCH_HEADER_PATTERN = re.compile(r"^@@ -(\d+),?(\d+)? \+(\d+),?(\d+)? @@")

MAX_REVIEW_RETRIES = 3

class CodeMonkey(Agent):
    save_dev_steps = True

    def __init__(self, project):
        super().__init__('code_monkey', project)

    def get_original_file(
            self,
            code_changes_description: str,
            step: dict[str, str],
            files: list[dict],
        ) -> tuple[str, str]:
        """
        Get the original file content and name.

        :param code_changes_description: description of the code changes
        :param step: information about the step being implemented
        :param files: list of files to send to the LLM
        :return: tuple of (file_name, file_content)
        """
        # If we're called as a result of debugging, we don't have the name/path of the file
        # to modify so we need to figure that out first.
        if 'path' not in step or 'name' not in step:
            file_to_change = self.identify_file_to_change(code_changes_description, files)
            step['path'] = os.path.dirname(file_to_change)
            step['name'] = os.path.basename(file_to_change)

        rel_path, abs_path = self.project.get_full_file_path(step['path'], step['name'])

        for f in files:
            # Take into account that step path might start with "/"
            if (f['path'] == step['path'] or (os.path.sep + f['path'] == step['path'])) and f['name'] == step['name'] and f['content']:
                file_content = f['content']
                break
        else:
            # If we didn't have the match (because of incorrect or double use of path separators or similar), fallback to directly loading the file
            try:
                file_content = get_file_contents(abs_path, self.project.root_path)['content']
                if isinstance(file_content, bytes):
                    # We should never want to change a binary file, but if we do end up here, let's not crash
                    file_content = "... <binary file, content omitted> ..."
            except ValueError:
                # File doesn't exist, we probably need to create a new one
                file_content = ""

        file_name = os.path.join(rel_path, step['name'])
        return file_name, file_content

    def implement_code_changes(
        self,
        convo: Optional[AgentConvo],
        step: dict[str, str],
    ) -> AgentConvo:
        """
        Implement code changes described in `code_changes_description`.

        :param convo: conversation to continue (must contain file coding/modification instructions)
        :param step: information about the step being implemented
        """
        code_change_description = step.get('code_change_description')

        files = self.project.get_all_coded_files()
        file_name, file_content = self.get_original_file(code_change_description, step, files)

        if file_content:
            print(f'Updating existing file {file_name}')
        else:
            print(f'Creating new file {file_name}')

        # Get the new version of the file
        content = self.replace_complete_file(
            convo,
            file_content,
            file_name,
            files,
        )

        for i in range(MAX_REVIEW_RETRIES):
            if not content or content == file_content:
                # There are no changes or there was problem talking with the LLM, we're done here
                break

            content, rework_feedback = self.review_change(convo, code_change_description, file_name, file_content, content)
            if not rework_feedback:
                # No rework needed, we're done here
                break

            content = convo.send_message('development/review_feedback.prompt', {
                "content": content,
                "original_content": file_content,
                "rework_feedback": rework_feedback,
            })
            if content:
                content = self.remove_backticks(content)

        # If we have changes, update the file
        if content and content != file_content:
            if not self.project.skip_steps:
                delta_lines = len(content.splitlines()) - len(file_content.splitlines())
                telemetry.inc("created_lines", delta_lines)
            self.project.save_file({
                'path': step['path'],
                'name': step['name'],
                'content': content,
            })

        return convo

    def replace_complete_file(
        self,
        convo: AgentConvo,
        file_content: str,
        file_name: str,
        files: list[dict]
    ) -> str:
        """
        As a fallback, replace the complete file content.

        This should only be used if we've failed to replace individual code blocks.

        :param convo: AgentConvo instance
        :param standalone: True if this is a standalone conversation
        :param code_changes_description: description of the code changes
        :param file_content: content of the file being updated
        :param file_name: name of the file being updated
        :param files: list of files to send to the LLM
        :return: updated file content

        Note: if even this fails for any reason, the original content is returned instead.
        """
        llm_response = convo.send_message('development/implement_changes.prompt', {
            "file_content": file_content,
            "file_name": file_name,
            "files": files,
        })
        convo.remove_last_x_messages(2)
        return self.remove_backticks(llm_response)

    @staticmethod
    def remove_backticks(content: str) -> str:
        """
        Remove optional backticks from the beginning and end of the content.

        :param content: content to remove backticks from
        :return: content without backticks
        """
        start_pattern = re.compile(r"^\s*```([a-z0-9]+)?\n")
        end_pattern = re.compile(r"\n```\s*$")
        content = start_pattern.sub("", content)
        content = end_pattern.sub("", content)
        return content

    def identify_file_to_change(self, code_changes_description: str, files: list[dict]) -> str:
        """
        Identify file to change based on the code changes description

        :param code_changes_description: description of the code changes
        :param files: list of files to send to the LLM
        :return: file to change
        """
        convo = AgentConvo(self)
        llm_response = convo.send_message('development/identify_files_to_change.prompt', {
            "code_changes_description": code_changes_description,
            "files": files,
        }, GET_FILE_TO_MODIFY)
        return llm_response["file"]

    def review_change(
        self,
        convo: AgentConvo,
        instructions: str,
        file_name: str,
        old_content: str,
        new_content: str
    ) -> tuple[str, str]:
        """
        Review changes that were applied to the file.

        This asks the LLM to act as a PR reviewer and for each part (hunk) of the
        diff, decide if it should be applied (kept) or ignored (removed from the PR).

        :param convo: AgentConvo instance
        :param instructions: instructions for the reviewer
        :param file_name: name of the file being modified
        :param old_content: old file content
        :param new_content: new file content (with proposed changes)
        :return: tuple with file content update with approved changes, and review feedback

        Diff hunk explanation: https://www.gnu.org/software/diffutils/manual/html_node/Hunks.html
        """

        hunks = self.get_diff_hunks(file_name, old_content, new_content)

        llm_response = convo.send_message('development/review_changes.prompt', {
            "instructions": instructions,
            "file_name": file_name,
            "old_content": old_content,
            "hunks": hunks,
        }, REVIEW_CHANGES)
        messages_to_remove = 2

        for i in range(MAX_REVIEW_RETRIES):
            reasons = {}
            ids_to_apply = set()
            ids_to_ignore = set()
            ids_to_rework = set()
            for hunk in llm_response.get("hunks", []):
                reasons[hunk["number"] - 1] = hunk["reason"]
                if hunk.get("decision", "").lower() == "apply":
                    ids_to_apply.add(hunk["number"] - 1)
                elif hunk.get("decision", "").lower() == "ignore":
                    ids_to_ignore.add(hunk["number"] - 1)
                elif hunk.get("decision", "").lower() == "rework":
                    ids_to_rework.add(hunk["number"] - 1)

            n_hunks = len(hunks)
            n_review_hunks = len(reasons)
            if n_review_hunks == n_hunks:
                break
            elif n_review_hunks < n_hunks:
                error = "Not all hunks have been reviewed. Please review all hunks and add 'apply', 'ignore' or 'rework' decision for each."
            elif n_review_hunks > n_hunks:
                error = f"Your review contains more hunks ({n_review_hunks}) than in the original diff ({n_hunks}). Note that one hunk may have multiple changed lines."

            # Max two retries; if the reviewer still hasn't reviewed all hunks, we'll just use the entire new content
            llm_response = convo.send_message(
                'utils/llm_response_error.prompt', {
                    "error": error
                },
                REVIEW_CHANGES,
            )
            messages_to_remove += 2
        else:
            # The reviewer failed to review all the hunks in 3 attempts, let's just use all the new content
            convo.remove_last_x_messages(messages_to_remove)
            return new_content

        convo.remove_last_x_messages(messages_to_remove)

        hunks_to_apply = [ h for i, h in enumerate(hunks) if i in ids_to_apply ]
        diff_log = f"--- {file_name}\n+++ {file_name}\n" + "\n".join(hunks_to_apply)

        hunks_to_rework = [ (i, h) for i, h in enumerate(hunks) if i in ids_to_rework ]
        review_log = "\n\n".join([
            f"## Change\n```{hunk}```\nReviewer feedback:\n{reasons[i]}" for (i, hunk) in hunks_to_rework
        ]) + "\n\nReview notes:\n" + llm_response["review_notes"]

        if len(hunks_to_apply) == len(hunks):
            print("Applying entire change")
            logger.info(f"Applying entire change to {file_name}")
            return new_content, None

        elif len(hunks_to_apply) == 0:
            if hunks_to_rework:
                print(f"Requesting rework for {len(hunks_to_rework)} changes with reason: {llm_response['review_notes']}")
                logger.info(f"Requesting rework for {len(hunks_to_rework)} changes to {file_name} (0 hunks to apply)")
                return old_content, review_log
            else:
                # If everything can be safely ignored, it's probably because the files already implement the changes
                # from previous tasks (which can happen often). Insisting on a change here is likely to cause problems.
                print(f"Rejecting entire change with reason: {llm_response['review_notes']}")
                logger.info(f"Rejecting entire change to {file_name} with reason: {llm_response['review_notes']}")
                return old_content, None

        print("Applying code change:\n" + diff_log)
        logger.info(f"Applying code change to {file_name}:\n{diff_log}")
        new_content = self.apply_diff(file_name, old_content, hunks_to_apply, new_content)
        if hunks_to_rework:
            print(f"Requesting rework for {len(hunks_to_rework)} changes with reason: {llm_response['review_notes']}")
            logger.info(f"Requesting further rework for {len(hunks_to_rework)} changes to {file_name}")
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

        hunks = re.split(r'\n@@', diff_txt, re.MULTILINE)
        result = []
        for i, h in enumerate(hunks):
            # Skip the prologue (file names)
            if i == 0:
                continue
            txt = h.splitlines()
            txt[0] = "@@" + txt[0]
            result.append("\n".join(txt))
        return result

    def apply_diff(
        self,
        file_name: str,
        old_content: str,
        hunks: list[str],
        fallback: str
    ):
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
        diff = "\n".join(
            [
                "--- " + file_name,
                "+++ " + file_name,
            ] + hunks
        ) + "\n"
        try:
            fixed_content = self._apply_patch(old_content, diff)
        except Exception as e:
            # This should never happen but if it does, just use the new version from
            # the LLM and hope for the best
            print(f"Error applying diff: {e}; hoping all changes are valid")
            trace_code_event(
                "patch-apply-error",
                {
                    "file": file_name,
                    "error": str(e),
                    "traceback": format_exc(),
                    "original": old_content,
                    "diff": diff
                }
            )
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

        updated_text = ''
        index_original = start_line = 0

        # Choose which group of the regex to use based on the revert flag
        match_index, line_sign = (1, '+') if not revert else (3, '-')

        # Skip header lines of the patch
        while index_original < len(patch_lines) and patch_lines[index_original].startswith(("---", "+++")):
            index_original += 1

        while index_original < len(patch_lines):
            match = PATCH_HEADER_PATTERN.match(patch_lines[index_original])
            if not match:
                raise Exception("Bad patch -- regex mismatch [line " + str(index_original) + "]")

            line_number = int(match.group(match_index)) - 1 + (match.group(match_index + 1) == '0')

            if start_line > line_number or line_number > len(original_lines):
                raise Exception("Bad patch -- bad line number [line " + str(index_original) + "]")

            updated_text += ''.join(original_lines[start_line:line_number])
            start_line = line_number
            index_original += 1

            while index_original < len(patch_lines) and patch_lines[index_original][0] != '@':
                if index_original + 1 < len(patch_lines) and patch_lines[index_original + 1][0] == '\\':
                    line_content = patch_lines[index_original][:-1]
                    index_original += 2
                else:
                    line_content = patch_lines[index_original]
                    index_original += 1

                if line_content:
                    if line_content[0] == line_sign or line_content[0] == ' ':
                        updated_text += line_content[1:]
                    start_line += (line_content[0] != line_sign)

        updated_text += ''.join(original_lines[start_line:])
        return updated_text
