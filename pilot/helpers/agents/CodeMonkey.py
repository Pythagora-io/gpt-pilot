import os.path
import re
from typing import Optional

from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from helpers.files import get_file_contents
from const.function_calls import GET_FILE_TO_MODIFY

from utils.exit import trace_code_event
from utils.telemetry import telemetry


class CodeMonkey(Agent):
    save_dev_steps = True

    # Only attempt block-by-block replace if the file is larger than this many lines
    SMART_REPLACE_THRESHOLD = 200

    def __init__(self, project, developer):
        super().__init__('code_monkey', project)
        self.developer = developer

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
        code_changes_description: str,
        step: dict[str, str],
    ) -> AgentConvo:
        """
        Implement code changes described in `code_changes_description`.

        :param convo: AgentConvo instance (optional)
        :param task_description: description of the task
        :param code_changes_description: description of the code changes
        :param step: information about the step being implemented
        :param step_index: index of the step to implement
        """
        standalone = False
        if not convo:
            standalone = True
            convo = AgentConvo(self)

        files = self.project.get_all_coded_files()
        file_name, file_content = self.get_original_file(code_changes_description, step, files)
        content = file_content

        # If the file is non-empty and larger than the threshold, attempt to replace individual code blocks
        if file_content and len(file_content.splitlines()) > self.SMART_REPLACE_THRESHOLD:
            replace_complete_file, content = self.replace_code_blocks(
                step,
                convo,
                standalone,
                code_changes_description,
                file_content,
                file_name,
                files,
            )
        else:
            # Just replace the entire file
            replace_complete_file = True

        # If this is a new file or replacing individual code blocks failed,
        # replace the complete file.
        if replace_complete_file:
            content = self.replace_complete_file(
                convo,
                standalone,
                code_changes_description,
                file_content,
                file_name, files
            )

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

    def replace_code_blocks(
        self,
        step: dict[str, str],
        convo: AgentConvo,
        standalone: bool,
        code_changes_description: str,
        file_content: str,
        file_name: str,
        files: list[dict]
    ):
        llm_response = convo.send_message('development/implement_changes.prompt', {
            "full_output": False,
            "standalone": standalone,
            "code_changes_description": code_changes_description,
            "file_content": file_content,
            "file_name": file_name,
            "files": files,
        })

        replace_complete_file = False
        exchanged_messages = 2
        content = file_content

        # Allow for up to 2 retries
        while exchanged_messages < 7:
            if re.findall('(old|existing).+code', llm_response, re.IGNORECASE):
                trace_code_event("codemonkey-file-update-error", {
                    "error": "old-code-comment",
                    "llm_response": llm_response,
                })
                llm_response = convo.send_message('utils/llm_response_error.prompt', {
                    "error": (
                        "You must not omit any code from NEW_CODE. "
                        "Please don't use coments like `// .. existing code goes here`."
                    )
                })
                exchanged_messages += 2
                continue

            # Split the response into pairs of old and new code blocks
            block_pairs = self.get_code_blocks(llm_response)

            if len(block_pairs) == 0:
                if "```" in llm_response:
                    # We know some code blocks were outputted but we couldn't find them
                    print("Unable to parse code blocks from LLM response, asking to retry")
                    trace_code_event("codemonkey-file-update-error", {
                        "error": "error-parsing-blocks",
                        "llm_response": llm_response,
                    })

                    # If updating is more complicated than just replacing the complete file, don't bother.
                    if len(llm_response) > len(file_content):
                        replace_complete_file = True
                        break

                    llm_response = convo.send_message('utils/llm_response_error.prompt', {
                        "error": "I can't find CURRENT_CODE and NEW_CODE blocks in your response, please try again."
                    })
                    exchanged_messages += 2
                    continue
                else:
                    print(f"No changes required for {step['name']}")
                    break

            # Replace old code blocks with new code blocks
            errors = []
            for i, (old_code, new_code) in enumerate(block_pairs):
                try:
                    old_code, new_code = self.dedent(old_code, new_code)
                    content = self.replace(content, old_code, new_code)
                except ValueError as err:
                    errors.append((i + 1, str(err)))

            if not errors:
                break

            trace_code_event("codemonkey-file-update-error", {
                "error": "replace-errors",
                "llm_response": llm_response,
                "details": errors,
            })
            print(f"{len(errors)} error(s) while trying to update file, asking LLM to retry")

            if len(llm_response) > len(file_content):
                # If updating is more complicated than just replacing the complete file, don't bother.
                replace_complete_file = True
                break

            # Otherwise, identify the problem block(s) and ask the LLM to retry
            if content != file_content:
                error_text = (
                    "Some changes were applied, but these failed:\n" +
                    "\n".join(f"Error in change {i}:\n{err}" for i, err in errors) +
                    "\nPlease fix the errors and try again (only output the blocks that failed to update, not all of them)."
                )
            else:
                error_text = "\n".join(f"Error in change {i}:\n{err}" for i, err in errors)

            llm_response = convo.send_message('utils/llm_response_error.prompt', {
                "error": error_text,
            })
            exchanged_messages += 2
        else:
            # We failed after a few retries, so let's just replace the complete file
            print("Unable to modify file, asking LLM to output the complete new file")
            replace_complete_file = True

        if replace_complete_file:
            trace_code_event("codemonkey-file-update-error", {
                "error": "fallback-complete-replace",
                "llm_response": llm_response,
            })

        convo.remove_last_x_messages(exchanged_messages)
        return replace_complete_file, content

    def replace_complete_file(
        self,
        convo: AgentConvo,
        standalone: bool,
        code_changes_description: str,
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
            "full_output": True,
            "standalone": standalone,
            "code_changes_description": code_changes_description,
            "file_content": file_content,
            "file_name": file_name,
            "files": files,
        })
        start_pattern = re.compile(r"^\s*```([a-z0-9]+)?\n")
        end_pattern = re.compile(r"\n```\s*$")
        llm_response = start_pattern.sub("", llm_response)
        llm_response = end_pattern.sub("", llm_response)
        return llm_response


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

    @staticmethod
    def get_code_blocks(llm_response: str) -> list[tuple[str, str]]:
        """
        Split the response into code block(s).

        Ignores any content outside of code blocks.

        :param llm_response: response from the LLM
        :return: list of pairs of current and new blocks
        """
        pattern = re.compile(
            r"CURRENT_CODE:\n```([a-z0-9]+)?\n(.*?)\n```\nNEW_CODE:\n```([a-z0-9]+)?\n(.*?)\n?```\nEND\s*",
            re.DOTALL
        )
        pairs = []
        for block in pattern.findall(llm_response):
            pairs.append((block[1], block[3]))
        return pairs

    @staticmethod
    def dedent(old_code: str, new_code: str) -> tuple[str, str]:
        """
        Remove common indentation from `old_code` and `new_code`.

        This is useful because the LLM will sometimes indent the code blocks MORE
        than in the original file, leading to no matches. Since we have indent
        compensation, we can just remove any extra indent as long as we do it
        consistently for both old and new code block.

        :param old_code: old code block
        :param new_code: new code block
        :return: tuple of (old_code, new_code) with common indentation removed
        """
        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()
        indent = 0
        while all(ol.startswith(" ") for ol in old_lines) and all(ol.startswith(" ") for ol in new_lines):
            indent -= 1
            old_lines = [ol[1:] for ol in old_lines]
            new_lines = [nl[1:] for nl in new_lines]
        return "\n".join(old_lines), "\n".join(new_lines)

    @staticmethod
    def replace(haystack: str, needle: str, replacement: str) -> str:
        """
        Replace `needle` text in `haystack`, allowing that `needle` is not
        indented the same as the matching part of `haystack` and
        compensating for it.

        :param haystack: text to search in
        :param needle: text to search for
        :param replacement: text to replace `needle` with
        :return: `haystack` with `needle` replaced with `replacement`

        Example:
        >>> haystack = "def foo():\n    pass"
        >>> needle = "pass"
        >>> replacement = "return 42"
        >>> replace(haystack, needle, replacement)
        "def foo():\n    return 42"

        If `needle` is not found in `haystack` even with indent compensation,
        or if it's found multiple times, raise a ValueError.
        """

        def indent_text(text: str, indent: int) -> str:
            return "\n".join((" " * indent + line) for line in text.splitlines())

        def indent_sensitive_match(haystack: str, needle: str) -> int:
            """
            Check if 'needle' is in 'haystack' but compare full lines.
            """
            # This is required so we don't match text "foo" (no indentation) with line "  foo"
            # (2 spaces indentation). We want exact matches so we know exact indentation needed.
            haystack_with_line_start_stop_markers = "\n".join(f"\x00{line}\x00" for line in haystack.splitlines())
            needle_with_line_start_stop_markers = "\n".join(f"\x00{line}\x00" for line in needle.splitlines())
            return haystack_with_line_start_stop_markers.count(needle_with_line_start_stop_markers)

        # Try from the largest indents to the smallest so that we know the correct indentation of
        # single-line old blocks that would otherwise match with 0 indent as well. If these single-line
        # old blocks were then replaced with multi-line blocks and indentation wasn't not correctly re-applied,
        # the new multiline block would only have the first line correctly indented. We want to avoid that.
        matching_old_blocks = []

        for indent in range(128, -1, -1):
            text = indent_text(needle, indent)
            if text not in haystack:
                # If there are empty lines in the old code, `indent_text` will indent them as well. The original
                # file might not have them indented as they're empty, so it is useful to try without indenting
                # those empty lines.
                text = "\n".join(
                    (line if line.strip() else "")
                    for line
                    in text.splitlines()
                )
            n_matches = indent_sensitive_match(haystack, text)
            for i in range(n_matches):
                matching_old_blocks.append((indent, text))

        if len(matching_old_blocks) == 0:
            raise ValueError(
                f"Old code block not found in the original file:\n```\n{needle}\n```\n"
                "Old block *MUST* contain the exact same text (including indentation, empty lines, etc.) as the original file "
                "in order to match."
            )

        if len(matching_old_blocks) > 1:
            raise ValueError(
                f"Old code block found more than once ({len(matching_old_blocks)} matches) in the original file:\n```\n{needle}\n```\n\n"
                "Please provide larger blocks (more context) to uniquely identify the code that needs to be changed."
            )

        indent, text = matching_old_blocks[0]
        indented_replacement = indent_text(replacement, indent)
        return haystack.replace(text, indented_replacement)
