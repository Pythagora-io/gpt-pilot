from enum import Enum
from typing import Tuple

import pytest
from pydantic import BaseModel, field_validator

from core.llm.parser import CodeBlockParser, EnumParser, JSONParser, MultiCodeBlockParser, OptionalCodeBlockParser


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("", []),
        ("some text without code blocks", []),
        ("```\n```", [""]),
        ("```py\n```", [""]),
        ("```py\nsome code\n```", ["some code"]),
        ("```py\nsome ``` code\n```", ["some ``` code"]),
        (
            "some text preamble\n" "```\nsome code\n```\n" "```py\nmore\ncode\n```\n" "some text conclusion",
            ["some code", "more\ncode"],
        ),
    ],
)
def test_multi_code_block_parser(input, expected):
    parser = MultiCodeBlockParser()
    assert parser(input) == expected


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("", None),
        ("some text without code blocks", None),
        ("```py\nsome code\n```", "some code"),
        ("```\nfirst\n```\n ... \n```\nsecond\n```", None),
    ],
)
def test_code_block_parser(input, expected):
    parser = CodeBlockParser()
    if expected is None:
        with pytest.raises(ValueError):
            parser(input)
    else:
        assert parser(input) == expected


@pytest.mark.parametrize(
    ("input", "strict", "expected"),
    [
        ("{}", True, {}),
        ('{"a": 1}', True, {"a": 1}),
        ('```json\n{"a": 1, "b": "c"}\n```', True, {"a": 1, "b": "c"}),
        ("", True, ValueError),
        ("", False, None),
        ("{bad json}", True, ValueError),
        ("{bad json}", False, None),
        ("```{", True, ValueError),
        ("```{", False, None),
        ('{"a": 1, "b": "c"}', False, {"a": 1, "b": "c"}),
    ],
)
def test_parse_json_no_spec(input, strict, expected):
    parser = JSONParser(strict=strict)
    if expected == ValueError:
        with pytest.raises(ValueError):
            parser(input)
    else:
        assert parser(input) == expected


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        (
            '{"name": "John", "children": [{"age": 1, "name": "Jane", "geo": [1.0, 2.0]}]}',
            {
                "name": "John",
                "children": [
                    {
                        "age": 1,
                        "name": "Jane",
                        "geo": (1.0, 2.0),
                    },
                ],
            },
        ),
        (
            '```\n{"name": "John", "children": [{"age": 1, "name": "Jane", "geo": [1.0, 2.0]}]}\n```',
            {
                "name": "John",
                "children": [
                    {
                        "age": 1,
                        "name": "Jane",
                        "geo": (1.0, 2.0),
                    },
                ],
            },
        ),
        (
            # age must not be negative
            '{"name": "John", "children": [{"age": -1, "name": "Jane", "geo": [1.0, 2.0]}]}',
            ValueError,
        ),
        (
            # missing required field children
            '{"name": "John"}',
            ValueError,
        ),
        (
            # incorrect type of children.geo.0 field
            '{"name": "John", "children": [{"age": 1, "name": "Jane", "geo": ["a", 2.0]}]',
            ValueError,
        ),
        (
            # incorrect tuple size
            '{"name": "John", "children": [{"age": 1, "name": "Jane", "geo": [1.0, 2.0, 3.0]}]',
            ValueError,
        ),
    ],
)
def test_parse_json_with_spec(input, expected):
    class ChildModel(BaseModel):
        age: int
        name: str
        geo: Tuple[float, float]

        @field_validator("age")
        def age_must_be_positive(cls, v):
            if v < 0:
                raise ValueError("age must be positive")
            return v

    class ParentModel(BaseModel):
        name: str
        children: list[ChildModel]

    parser = JSONParser(spec=ParentModel)
    if expected is ValueError:
        with pytest.raises(ValueError):
            parser(input)
    else:
        result = parser(input)
        assert result.model_dump() == {**expected, "original_response": input.strip()}


def test_parse_json_schema():
    class TestModel(BaseModel):
        name: str
        age: int

    parser = JSONParser(spec=TestModel)
    assert parser.schema == {
        "title": "TestModel",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "string",
            },
            "age": {
                "title": "Age",
                "type": "integer",
            },
        },
        "required": ["name", "age"],
    }


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("", ValueError),
        ("first", "first"),
        ("SECOND", "second"),
        ("  third  ", "third"),
        ("fourth", ValueError),
    ],
)
def test_enum_parser(input, expected):
    class Choices(Enum):
        FIRST = "first"
        SECOND = "second"
        THIRD = "third"

    parser = EnumParser(Choices)
    if expected is ValueError:
        with pytest.raises(ValueError):
            parser(input)
    else:
        assert parser(input).value == expected


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("abc", "abc"),
        ("watch this: `foo`", "watch this: `foo`"),
        ("`hello world`", "hello world"),
        ("```\nhello world\n```", "hello world"),
    ],
)
def test_optional_block_parser(input, expected):
    parser = OptionalCodeBlockParser()
    assert parser(input) == expected
