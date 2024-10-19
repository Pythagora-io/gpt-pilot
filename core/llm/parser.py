import json
import re
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ValidationError, create_model


class MultiCodeBlockParser:
    """
    Parse multiple Markdown code blocks from a string.

    Expects zero or more blocks, and ignores any text
    outside of the code blocks.

    Example usage:

    >>> parser = MultiCodeBlockParser()
    >>> text = '''
    ... text outside block
    ...
    ... ```python
    ... first block
    ... ```
    ... some text between blocks
    ... ```js
    ... more
    ... code
    ... ```
    ... some text after blocks
    '''
    >>> assert parser(text) == ["first block", "more\ncode"]

    If no code blocks are found, an empty list is returned:
    """

    def __init__(self):
        self.pattern = re.compile(r"^```([a-z0-9]+\n)?(.*?)^```\s*", re.DOTALL | re.MULTILINE)

    def __call__(self, text: str) -> list[str]:
        blocks = []
        for block in self.pattern.findall(text):
            blocks.append(block[1].strip())
        return blocks


class CodeBlockParser(MultiCodeBlockParser):
    """
    Parse a Markdown code block from a string.

    Expects exactly one code block, and ignores
    any text before or after it.

    Usage:
    >>> parser = CodeBlockParser()
    >>> text = "text\n```py\ncodeblock\n'''\nmore text"
    >>> assert parser(text) == "codeblock"

    This is a special case of MultiCodeBlockParser,
    checking that there's exactly one block.
    """

    def __call__(self, text: str) -> str:
        blocks = super().__call__(text)
        # FIXME: if there are more than 1 code block, this means the output actually contains ```,
        # so re-parse this with that in mind
        if len(blocks) != 1:
            raise ValueError(f"Expected a single code block, got {len(blocks)}")
        return blocks[0]


class OptionalCodeBlockParser(MultiCodeBlockParser):
    def __call__(self, text: str) -> str:
        blocks = super().__call__(text)
        # FIXME: if there are more than 1 code block, this means the output actually contains ```,
        # so re-parse this with that in mind
        if len(blocks) > 1:
            raise ValueError(f"Expected a single code block, got {len(blocks)}")
        if len(blocks) == 0:
            return text.strip()
        return blocks[0]


class JSONParser:
    def __init__(self, spec: Optional[BaseModel] = None, strict: bool = True):
        self.spec = spec
        self.strict = strict or (spec is not None)
        self.original_response = None

    @property
    def schema(self):
        return self.spec.model_json_schema() if self.spec else None

    @staticmethod
    def errors_to_markdown(errors: list) -> str:
        error_txt = []
        for error in errors:
            loc = ".".join(str(loc) for loc in error["loc"])
            etype = error["type"]
            msg = error["msg"]
            error_txt.append(f"- `{loc}`: {etype} ({msg})")
        return "\n".join(error_txt)

    def __call__(self, text: str) -> Union[BaseModel, dict, None]:
        self.original_response = text.strip()  # Store the original text
        text = self.original_response
        if text.startswith("```"):
            try:
                text = CodeBlockParser()(text)
            except ValueError:
                if self.strict:
                    raise
                else:
                    return None

        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError as e:
            if self.strict:
                raise ValueError(f"JSON is not valid: {e}") from e
            else:
                return None
        if self.spec is None:
            return data

        try:
            model = self.spec(**data)
        except ValidationError as err:
            errtxt = self.errors_to_markdown(err.errors())
            raise ValueError(f"Invalid JSON format:\n{errtxt}") from err
        except Exception as err:
            raise ValueError(f"Error parsing JSON: {err}") from err

        # Create a new model that includes the original model fields and the original text
        ExtendedModel = create_model(
            f"Extended{self.spec.__name__}",
            original_response=(str, ...),
            **{field_name: (field.annotation, field.default) for field_name, field in self.spec.__fields__.items()},
        )

        # Instantiate the extended model
        extended_model = ExtendedModel(original_response=self.original_response, **model.dict())

        return extended_model


class EnumParser:
    def __init__(self, spec: Enum, ignore_case: bool = True):
        self.spec = spec
        self.ignore_case = ignore_case

    def __call__(self, text: str) -> Enum:
        text = text.strip()
        if self.ignore_case:
            text = text.lower()
        try:
            return self.spec(text)
        except ValueError as e:
            options = ", ".join([str(v) for v in self.spec])
            raise ValueError(f"Invalid option '{text}'; valid options: {options}") from e


class StringParser:
    def __call__(self, text: str) -> str:
        # Strip any leading and trailing whitespace
        text = text.strip()

        # Check and remove quotes at the start and end if they match
        if text.startswith(("'", '"')) and text.endswith(("'", '"')) and len(text) > 1:
            # Remove the first and last character if they are both quotes
            if text[0] == text[-1]:
                text = text[1:-1]

        return text
