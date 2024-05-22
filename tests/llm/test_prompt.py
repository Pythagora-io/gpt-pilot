import pytest
from jinja2 import UndefinedError

from core.llm.prompt import FormatTemplate, JinjaFileTemplate, JinjaStringTemplate


def test_format_template():
    template = FormatTemplate()
    assert (
        template(
            "hello {name}, you are {age:.2f} bn years old",
            name="world",
            age=4.54,
        )
        == "hello world, you are 4.54 bn years old"
    )


def test_jinja_string_template():
    template = JinjaStringTemplate()

    test_template = """
    hello <{{ name }}>,
    {% if age > 0 %}
    you are {{ age }} bn years old
    {% endif %}
    """

    expected_output = """
    hello <world>,
    you are 4.54 bn years old
    """

    assert template(test_template, name="world", age=4.54) == expected_output


def test_jinja_template_catches_undefined_variable():
    template = JinjaStringTemplate()

    with pytest.raises(UndefinedError, match="is undefined"):
        template("hello {{ world }}")


def test_jinja_file_template():
    template = JinjaFileTemplate(["tests/llm/prompts"])

    assert (
        template(
            "test.txt",
            name="world",
            age=4.54,
        )
        == "hello world,\nyou are 4.54 bn years old\n"
    )


def test_jinja_file_template_nonexistent_directory():
    with pytest.raises(ValueError):
        JinjaFileTemplate(["nonexistent"])
