import os.path
import re
from typing import Optional

from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from helpers.files import get_file_contents
from logger.logger import logger


class CodeMonkey(Agent):
    save_dev_steps = True

    def __init__(self, project, developer):
        super().__init__('code_monkey', project)
        self.developer = developer

    def implement_code_changes(
        self,
        convo: Optional[AgentConvo],
        task_description: str,
        code_changes_description: str,
        step: dict[str, str],
        step_index: int = 0,
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

        # If we're called as a result of debugging, we don't have the name/path of the file
        # to modify so we need to figure that out first.
        if 'path' not in step or 'name' not in step:
            files_to_change = self.identify_files_to_change(code_changes_description, files)

            if len(files_to_change) == 0:
                # This should never happen, but let's not crash if it does
                logger.warning(f"No relevant files found for code change: {code_changes_description}")
                return convo

            # In practice, we always have exactly one file to change, so we can just pick the first in
            # the list.
            step['path'] = os.path.dirname(files_to_change[0])
            step['name'] = os.path.basename(files_to_change[0])

        rel_path, abs_path = self.project.get_full_file_path(step['path'], step['name'])

        for f in files:
            # Take into account that step path might start with "/"
            if (f['path'] == step['path'] or (os.path.sep + f['path'] == step['path'])) and f['name'] == step['name'] and f['content']:
                file_content = f['content']
                break
        else:
            # If we didn't have the match (because of incorrect or double use of path separators or similar), fallback to directly loading the file
            file_content = get_file_contents(abs_path, self.project.root_path)['content']
            if isinstance(file_content, bytes):
                file_content = "... <binary file, content omitted> ..."

        file_name = os.path.join(rel_path, step['name'])

        llm_response = convo.send_message('development/implement_changes.prompt', {
            "full_output": False,
            "standalone": standalone,
            "code_changes_description": code_changes_description,
            "file_content": file_content,
            "file_name": file_name,
            "files": files,
        })

        exchanged_messages = 2
        replace_complete_file = False

        # Allow for up to 2 retries
        while exchanged_messages < 7:
            # Modify a copy of the content in case we need to retry
            content = file_content

            if re.findall('(old|existing).+code', llm_response, re.IGNORECASE):
                llm_response = convo.send_message('utils/llm_response_error.prompt', {
                    "error": (
                        "You must not omit any code from NEW_CODE. "
                        "Please don't use coments like `// .. existing code goes here`."
                    )
                })
                exchanged_messages += 2
                continue

            # Split the response into pairs of old and new code blocks
            blocks = self.get_code_blocks(llm_response)

            if len(blocks) == 0:
                print(f"No changes required for {step['name']}")
                break

            if len(blocks) % 2 != 0:
                print(f"Incorrect number of old→new code blocks ({len(blocks)}) when updating file, asking LLM to retry")

                # If updating is more complicated than just replacing the complete file, don't bother.
                if len(llm_response) > len(file_content):
                    replace_complete_file = True
                    break

                llm_response = convo.send_message('utils/llm_response_error.prompt', {
                    "error": "Each change should contain exactly one old and exactly one block of code."
                })
                exchanged_messages += 2
                continue

            # Replace old code blocks with new code blocks
            errors = []
            for i, (old_code, new_code) in enumerate(zip(blocks[::2], blocks[1::2])):
                try:
                    old_code, new_code = self.dedent(old_code, new_code)
                    content = self.replace(content, old_code, new_code)
                except ValueError as err:
                    errors.append((i + 1, str(err)))

            if not errors:
                break

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
            print(f"Unable to modify file, asking LLM to output the complete new file")
            replace_complete_file = True

        if replace_complete_file:
            content = self.replace_complete_file(
                convo,
                standalone,
                code_changes_description,
                file_content,
                file_name, files
            )
            blocks = self.get_code_blocks(llm_response)

        if content and content != file_content:
            self.project.save_file({
                'path': step['path'],
                'name': step['name'],
                'content': content,
            })

        convo.remove_last_x_messages(exchanged_messages)
        return convo

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
        blocks = self.get_code_blocks(llm_response)
        if len(blocks) != 1:
            logger.warning(f"Unable to implement code changes after 5 retries and a fallback: {code_changes_description}")
            return file_content

        return blocks[0]


    def identify_files_to_change(self, code_changes_description: str, files: list[dict]) -> list[str]:
        """
        Identify files to change based on the code changes description

        We really just want one file, but this can handle mutliple files
        and will return them all, or an empty list if no files are
        returned.

        :param code_changes_description: description of the code changes
        :param files: list of files to send to the LLM
        :return: list of files to change
        """
        convo = AgentConvo(self)
        llm_response = convo.send_message('development/identify_files_to_change.prompt', {
            "code_changes_description": code_changes_description,
            "files": files,
        })
        blocks = self.get_code_blocks(llm_response)
        files = []
        for block in blocks:
            for line in block.splitlines():
                files.append(line.strip())
        return files

    @staticmethod
    def get_code_blocks(llm_response: str) -> list[str]:
        """
        Split the response into code block(s).

        Ignores any content outside of code blocks.

        :param llm_response: response from the LLM
        :return: list of code blocks
        """
        pattern = re.compile(r"```([a-z0-9]+)?\n(.*?)\n```\s*", re.DOTALL)
        blocks = []
        for block in pattern.findall(llm_response):
            blocks.append(block[1])
        return blocks

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
        while all(l.startswith(" ") for l in old_lines) and all(l.startswith(" ") for l in new_lines):
            indent -= 1
            old_lines = [l[1:] for l in old_lines]
            new_lines = [l[1:] for l in new_lines]
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
