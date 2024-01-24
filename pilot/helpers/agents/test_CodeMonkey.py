from unittest.mock import patch, MagicMock, call
from os.path import normpath, sep
import pytest


from helpers.agents.CodeMonkey import CodeMonkey
from const.function_calls import GET_FILE_TO_MODIFY

@pytest.mark.parametrize(
    ("content", "expected_blocks"),
    [
        ("", []),
        ("no code blocks here", []),
        ("one\n```\ncode block\n```\nwithout CURRENT/NEW tags", []),
        (
            "Change\nCURRENT_CODE:\n```python\nold\n```\nNEW_CODE:\n```\nnew\n```\nEND\n",
            [("old", "new")]
        ),
        (
            "\n".join([
                "Change 1",
                "CURRENT_CODE:",
                "```python",
                "old",
                "```",
                "NEW_CODE:",
                "```javascript",
                "```",
                "END",
                "Change 2",
                "CURRENT_CODE:",
                "```python",
                "old",
                "```",
                "NEW_CODE:",
                "```python",
                "new",
                "```",
                "END",
            ]),
            [("old", ""), ("old", "new")]
        ),
        (
            "\n".join([
                "Code with markdown blocks in it",
                "CURRENT_CODE:",
                "```markdown",
                "# Title",
                "",
                "```python",
                "print('hello world')",
                "```",
                "Rest of markdown",
                "```",
                "NEW_CODE:",
                "```markdown",
                "# Title",
                "",
                "```python",
                "print('goodbye world')",
                "```",
                "New markdown text here",
                "```",
                "END"
            ]),
            [
                (
                    "# Title\n\n```python\nprint('hello world')\n```\nRest of markdown",
                    "# Title\n\n```python\nprint('goodbye world')\n```\nNew markdown text here",
                )
            ]
        )
    ]
)
def test_get_code_blocks(content, expected_blocks):
    code_monkey = CodeMonkey(None, None)
    assert code_monkey.get_code_blocks(content) == expected_blocks


@pytest.mark.parametrize(
    ("haystack", "needle", "result", "error"),
    [
        ### Oneliner old blocks ###
        # Simple match
        ("first\nsecond\nthird", "second", "first\n@@NEW@@\nthird", None),
        # No match
        ("first\nsecond\nthird", "fourth", None, "not found"),
        # Too many matches on the same indentation level
        ("line\nline", "line", None, "found more than once"),
        # Match, replacement should be indented
        ("first\n    second\nthird", "second", "first\n    @@NEW@@\nthird", None),
        # Too many matches, on different indentation levels
        ("line\n  line", "line", None, "found more than once"),

        ### Multiline old blocks ###
        # Simple match
        ("first\nsecond\nthird", "second\nthird", "first\n@@NEW@@", None),
        # No match
        ("first\nsecond\nthird", "second\n  third", None, "not found"),
        # Too many matches on the same indentation level
        ("a\nb\nc\nd\na\nb", "a\nb", None, "found more than once"),
        # Too many matches on different indentation levels
        ("a\nb\nc\nd\n  a\n  b", "a\nb", None, "found more than once"),
        # Match, replacement should be indented
        ("first\n  second\n  third", "second\nthird", "first\n  @@NEW@@", None),

        ### Multiline with empty lines ###
        # Simple match
        ("first\nsecond\n\nthird", "second\n\nthird", "first\n@@NEW@@", None),
        # Indented match with empty lines also indentend
        ("first\n  second\n  \n  third", "second\n\nthird", "first\n  @@NEW@@", None),
        # Indented match with empty lines not indentend
        ("first\n  second\n\n  third", "second\n\nthird", "first\n  @@NEW@@", None),
    ]
)
def test_replace(haystack, needle, result, error):
    code_monkey = CodeMonkey(None, None)
    if error:
        with pytest.raises(ValueError, match=error):
            code_monkey.replace(haystack, needle, "@@NEW@@")
    else:
        assert code_monkey.replace(haystack, needle, "@@NEW@@") == result


@patch("helpers.agents.CodeMonkey.AgentConvo")
def test_identify_file_to_change(MockAgentConvo):
    mock_convo = MockAgentConvo.return_value
    mock_convo.send_message.return_value = {"file": "file.py"}
    files = CodeMonkey(None, None).identify_file_to_change("some description", [])
    assert files == "file.py"
    mock_convo.send_message.assert_called_once_with(
        "development/identify_files_to_change.prompt",
        {
            "code_changes_description": "some description",
            "files": []
        },
        GET_FILE_TO_MODIFY
    )


def test_dedent():
    old_code = "\n".join([
        "    def foo():",
        "        print('bar')",
    ])
    new_code = "\n".join([
        "  def bar():",
        "      print('foo')",
    ])
    expected_old = "\n".join([
        "  def foo():",
        "      print('bar')",
    ])
    expected_new = "\n".join([
        "def bar():",
        "    print('foo')",
    ])
    result_old, result_new = CodeMonkey.dedent(old_code, new_code)
    assert result_old == expected_old
    assert expected_new == result_new


def test_codemonkey_simple():
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = [
        {
            "path": "",
            "name": "main.py",
            "content": "one to the\nfoo\nto the three to the four"
        },
    ]
    mock_project.get_full_file_path.return_value = ("", normpath("/path/to/main.py"))
    mock_convo = MagicMock()
    mock_convo.send_message.return_value = "## Change\nCURRENT_CODE:\n```\nfoo\n```\nNEW_CODE:\n```\nbar\n```\nEND"

    cm = CodeMonkey(mock_project, None)
    with patch.object(cm, "SMART_REPLACE_THRESHOLD", 1):
        cm.implement_code_changes(
            mock_convo,
            "Modify all references from `foo` to `bar`",
            {
                "path": sep,
                "name": "main.py",
            }
        )

    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with(sep, "main.py")
    mock_convo.send_message.assert_called_once_with(
        "development/implement_changes.prompt", {
        "full_output": False,
        "standalone": False,
        "code_changes_description": "Modify all references from `foo` to `bar`",
        "file_content": "one to the\nfoo\nto the three to the four",
        "file_name": "main.py",
        "files": mock_project.get_all_coded_files.return_value,
    })
    mock_project.save_file.assert_called_once_with({
        "path": sep,
        "name": "main.py",
        "content": "one to the\nbar\nto the three to the four"
    })


def test_codemonkey_simple_replace():
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = [
        {
            "path": "",
            "name": "main.py",
            "content": "one to the\nfoo\nto the three to the four"
        },
    ]
    mock_project.get_full_file_path.return_value = ("", normpath("/path/to/main.py"))
    mock_convo = MagicMock()
    mock_convo.send_message.return_value = "```\none to the\nbar\nto the three to the four\n```"

    cm = CodeMonkey(mock_project, None)
    cm.implement_code_changes(
        mock_convo,
        "Modify all references from `foo` to `bar`",
        {
            "path": sep,
            "name": "main.py",
        }
    )

    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with(sep, "main.py")
    mock_convo.send_message.assert_called_once_with(
        "development/implement_changes.prompt", {
        "full_output": True,
        "standalone": False,
        "code_changes_description": "Modify all references from `foo` to `bar`",
        "file_content": "one to the\nfoo\nto the three to the four",
        "file_name": "main.py",
        "files": mock_project.get_all_coded_files.return_value,
    })
    mock_project.save_file.assert_called_once_with({
        "path": sep,
        "name": "main.py",
        "content": "one to the\nbar\nto the three to the four"
    })


@patch("helpers.agents.CodeMonkey.trace_code_event")
def test_codemonkey_retry(trace_code_event):
    file_content = (
        "one to the\nfoo\nto the three to the four\n"
        "the rest of this file is filler so it's big enought not to "
        "trigger the full replace fallback immediately upon the first failure"
    )
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = [
        {
            "path": "",
            "name": "main.py",
            "content": file_content,
        },
    ]
    mock_project.get_full_file_path.return_value = ("", normpath("/path/to/main.py"))
    mock_convo = MagicMock()
    mock_convo.send_message.side_effect = [
        # Incorrect match
        "## Change\nCURRENT_CODE:\n```\ntwo\n```\nNEW_CODE:\n```\nbar\n```\nEND\n",
        # Corrected match on retry
        "Apologies, here is the corrected version. ## Change\nCURRENT_CODE:\n```\n  foo\n```\nNEW_CODE:\n```\n  bar\n```\nEND\n",
    ]

    cm = CodeMonkey(mock_project, None)
    with patch.object(cm, "SMART_REPLACE_THRESHOLD", 1):
        cm.implement_code_changes(
            mock_convo,
            "Modify all references from `foo` to `bar`",
            {
                "path": sep,
                "name": "main.py",
            }
        )

    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with(sep, "main.py")
    mock_convo.send_message.assert_has_calls([
        call(
            "development/implement_changes.prompt", {
                "full_output": False,
                "standalone": False,
                "code_changes_description": "Modify all references from `foo` to `bar`",
                "file_content": file_content,
                "file_name": "main.py",
                "files": mock_project.get_all_coded_files.return_value,
            }
        ),
        call(
            "utils/llm_response_error.prompt", {
                "error": (
                    "Error in change 1:\n"
                    "Old code block not found in the original file:\n```\ntwo\n```\n"
                    "Old block *MUST* contain the exact same text (including indentation, empty lines, etc.) "
                    "as the original file in order to match."
                ),
            }
        )
    ])
    mock_project.save_file.assert_called_once_with({
        "path": sep,
        "name": "main.py",
        "content": file_content.replace("foo", "bar"),
    })
    trace_code_event.assert_called_once_with(
        "codemonkey-file-update-error",
        {
            "error": "replace-errors",
            "llm_response": "## Change\nCURRENT_CODE:\n```\ntwo\n```\nNEW_CODE:\n```\nbar\n```\nEND\n",
            "details": [(1, (
                'Old code block not found in the original file:\n```\ntwo\n```\n'
                'Old block *MUST* contain the exact same text (including indentation, empty lines, etc.) '
                'as the original file in order to match.'
            ))]
        }
    )


@patch("helpers.agents.CodeMonkey.trace_code_event")
def test_codemonkey_partial_retry(trace_code_event):
    file_content = (
        "one to the\nfoo\nto the three to the four\n"
        "the rest of this file is filler so it's big enought not to\n"
        "trigger\nthe full replace fallback immediately upon the first failure"
    )
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = [
        {
            "path": "",
            "name": "main.py",
            "content": file_content,
        },
    ]
    mock_project.get_full_file_path.return_value = ("", normpath("/path/to/main.py"))
    mock_convo = MagicMock()
    mock_convo.send_message.side_effect = [
        # Incorrect match
        (
            "## Change 1\nCURRENT_CODE:\n```\ntwo\n```\nNEW_CODE:\n```\nbar\n```\nEND\n"
            "## Change 2\nCURRENT_CODE:\n```\ntrigger\n```\nNEW_CODE:\n```\ncause\n```\nEND\n"
        ),
        "Apologies, here is the corrected version. ## Change 1\nCURRENT_CODE:\n```\n  foo\n```\nNEW_CODE:\n```\n  bar\n```\nEND\n",
    ]

    cm = CodeMonkey(mock_project, None)
    with patch.object(cm, "SMART_REPLACE_THRESHOLD", 1):
        cm.implement_code_changes(
            mock_convo,
            "Modify all references from `foo` to `bar` and `trigger` to `cause`",
            {
                "path": sep,
                "name": "main.py",
            }
        )

    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with(sep, "main.py")
    mock_convo.send_message.assert_has_calls([
        call(
            "development/implement_changes.prompt", {
                "full_output": False,
                "standalone": False,
                "code_changes_description": "Modify all references from `foo` to `bar` and `trigger` to `cause`",
                "file_content": file_content,
                "file_name": "main.py",
                "files": mock_project.get_all_coded_files.return_value,
            }
        ),
        call(
            "utils/llm_response_error.prompt", {
                "error": (
                    "Some changes were applied, but these failed:\n"
                    "Error in change 1:\n"
                    "Old code block not found in the original file:\n```\ntwo\n```\n"
                    "Old block *MUST* contain the exact same text (including indentation, empty lines, etc.) "
                    "as the original file in order to match.\n"
                    "Please fix the errors and try again (only output the blocks that failed to update, not all of them)."
                ),
            }
        )
    ])
    mock_project.save_file.assert_called_once_with({
        "path": sep,
        "name": "main.py",
        "content": file_content.replace("foo", "bar").replace("trigger", "cause")
    })
    trace_code_event.assert_called_once_with(
        "codemonkey-file-update-error",
        {
            "error": "replace-errors",
            "llm_response": (
                "## Change 1\nCURRENT_CODE:\n```\ntwo\n```\nNEW_CODE:\n```\nbar\n```\nEND\n"
                "## Change 2\nCURRENT_CODE:\n```\ntrigger\n```\nNEW_CODE:\n```\ncause\n```\nEND\n"
            ),
            "details": [(1, (
                'Old code block not found in the original file:\n```\ntwo\n```\n'
                'Old block *MUST* contain the exact same text (including indentation, empty lines, etc.) '
                'as the original file in order to match.'
            ))]
        }
    )


@patch("helpers.agents.CodeMonkey.trace_code_event")
def test_codemonkey_fallback(trace_code_event):
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = [
        {
            "path": "",
            "name": "main.py",
            "content": "one to the\nfoo\nto the three to the four"
        },
    ]
    mock_project.get_full_file_path.return_value = ("", normpath("/path/to/main.py"))
    mock_convo = MagicMock()
    mock_convo.send_message.side_effect = [
        # Incorrect match (END within block), will cause immediate fallback because of short file
        "1 ## Change\nCURRENT_CODE:\n```\nfoo\n```\nNEW_CODE:\n```\nbar\nEND\n```\n",
        # Fallback returns entire new file
        "```\none to the\nbar\nto the three to the four\n```\n",
    ]

    cm = CodeMonkey(mock_project, None)
    with patch.object(cm, "SMART_REPLACE_THRESHOLD", 1):
        cm.implement_code_changes(
            mock_convo,
            "Modify all references from `foo` to `bar`",
            {
                "path": sep,
                "name": "main.py",
            }
        )

    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with(sep, "main.py")
    mock_convo.send_message.assert_has_calls([
        call(
            "development/implement_changes.prompt", {
                "full_output": False,
                "standalone": False,
                "code_changes_description": "Modify all references from `foo` to `bar`",
                "file_content": "one to the\nfoo\nto the three to the four",
                "file_name": "main.py",
                "files": mock_project.get_all_coded_files.return_value,
            }
        ),
        call(
            'development/implement_changes.prompt', {
                "full_output": True,
                "standalone": False,
                "code_changes_description": "Modify all references from `foo` to `bar`",
                "file_content": "one to the\nfoo\nto the three to the four",
                "file_name": "main.py",
                "files": mock_project.get_all_coded_files.return_value,
            }
        )
    ])
    mock_project.save_file.assert_called_once_with({
        "path": sep,
        "name": "main.py",
        "content": "one to the\nbar\nto the three to the four"
    })
    trace_code_event.assert_has_calls([
        call(
            'codemonkey-file-update-error',
            {
                'error': 'error-parsing-blocks',
                'llm_response': '1 ## Change\nCURRENT_CODE:\n```\nfoo\n```\nNEW_CODE:\n```\nbar\nEND\n```\n'
            }
        ),
        call(
            'codemonkey-file-update-error',
            {
                'error': 'fallback-complete-replace',
                'llm_response': '1 ## Change\nCURRENT_CODE:\n```\nfoo\n```\nNEW_CODE:\n```\nbar\nEND\n```\n'
            }
        )
    ])


@patch("helpers.agents.CodeMonkey.trace_code_event")
@patch("helpers.agents.CodeMonkey.get_file_contents")
@patch("helpers.agents.CodeMonkey.AgentConvo")
def test_codemonkey_implement_changes_after_debugging(MockAgentConvo, mock_get_file_contents, trace_code_event):
    """
    Test that the flow to figure out files that need to be changed
    (which happens after debugging where we only have a description of the
    changes needed, not file name).

    Also test standalone conversation (though that's not happening after debugging).
    """
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = []
    mock_project.get_full_file_path.return_value = ("", "/path/to/main.py")
    mock_convo = MockAgentConvo.return_value
    mock_convo.send_message.return_value = "## Change\nCURRENT_CODE:\n```\nfoo\n```\nNEW_CODE:\n```\nbar\n```\nEND"
    mock_get_file_contents.return_value = {
        "name": "main.py",
        "path": "",
        "content": "one to the\nfoo\nto the three to the four",
        "full_path": "/path/to/main.py",
    }

    cm = CodeMonkey(mock_project, None)
    with patch.object(cm, "identify_file_to_change") as mock_identify_file_to_change:
        with patch.object(cm, "SMART_REPLACE_THRESHOLD", 1):
            mock_identify_file_to_change.return_value = "/main.py"
            cm.implement_code_changes(
                None,
                "Modify all references from `foo` to `bar`",
                {},
            )

    MockAgentConvo.assert_called_once_with(cm)
    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with("/", "main.py")
    mock_convo.send_message.assert_called_once_with(
        "development/implement_changes.prompt", {
        "full_output": False,
        "standalone": True,
        "code_changes_description": "Modify all references from `foo` to `bar`",
        "file_content": "one to the\nfoo\nto the three to the four",
        "file_name": "main.py",
        "files": mock_project.get_all_coded_files.return_value,
    })
    mock_project.save_file.assert_called_once_with({
        "path": "/",
        "name": "main.py",
        "content": "one to the\nbar\nto the three to the four"
    })
    trace_code_event.assert_not_called()


@patch("helpers.agents.CodeMonkey.trace_code_event")
@patch("helpers.agents.CodeMonkey.get_file_contents")
def test_codemonkey_original_file_not_found(mock_get_file_contents, _trace_code_event):
    mock_project = MagicMock()
    mock_project.get_all_coded_files.return_value = []
    mock_project.get_full_file_path.return_value = ("", normpath("/path/to/main.py"))
    mock_convo = MagicMock()
    mock_convo.send_message.return_value = "```\none to the\nbar\nto the three to the four\n```\n"
    mock_get_file_contents.side_effect = ValueError("File not found: /path/to/main.py")
    cm = CodeMonkey(mock_project, None)
    with patch.object(cm, "SMART_REPLACE_THRESHOLD", 1):
        cm.implement_code_changes(
            mock_convo,
            "Modify all references from `foo` to `bar`",
            {
                "path": sep,
                "name": "main.py",
            }
        )

    mock_project.get_all_coded_files.assert_called_once()
    mock_project.get_full_file_path.assert_called_once_with(sep, "main.py")
    mock_convo.send_message.assert_called_once_with(
        'development/implement_changes.prompt', {
            "full_output": True,
            "standalone": False,
            "code_changes_description": "Modify all references from `foo` to `bar`",
            "file_content": "",
            "file_name": "main.py",
            "files": mock_project.get_all_coded_files.return_value,
        }
    )
    mock_project.save_file.assert_called_once_with({
        "path": sep,
        "name": "main.py",
        "content": "one to the\nbar\nto the three to the four"
    })
