import json
import re
from typing import Union, TypeVar, List, Dict, Literal, Optional, TypedDict, Callable

JsonTypeBase = Union[str, int, float, bool, None, List["JsonType"], Dict[str, "JsonType"]]
JsonType = TypeVar("JsonType", bound=JsonTypeBase)


class FunctionParameters(TypedDict):
    """Function parameters"""

    type: Literal["object"]
    properties: dict[str, JsonType]
    required: Optional[list[str]]


class FunctionType(TypedDict):
    """Function type"""

    name: str
    description: Optional[str]
    parameters: FunctionParameters


class FunctionCall(TypedDict):
    """Function call"""

    name: str
    parameters: str


class FunctionCallSet(TypedDict):
    definitions: list[FunctionType]
    functions: dict[str, Callable]


def add_function_calls_to_request(gpt_data, function_calls: Union[FunctionCallSet, None]):
    if function_calls is None:
        return None

    model: str = gpt_data['model']
    is_instruct = 'llama' in model or 'anthropic' in model

    gpt_data['functions'] = function_calls['definitions']

    prompter = JsonPrompter(is_instruct)

    if len(function_calls['definitions']) > 1:
        function_call = None
    else:
        function_call = function_calls['definitions'][0]['name']

    function_call_message = {
        'role': 'user',
        'content': prompter.prompt('', function_calls['definitions'], function_call)
    }
    gpt_data['messages'].append(function_call_message)

    return function_call_message


def parse_agent_response(response, function_calls: Union[FunctionCallSet, None]):
    """
    Post-processes the response from the agent.

    Args:
        response: The response from the agent.
        function_calls: Optional function calls associated with the response.

    Returns: The post-processed response.
    """
    if function_calls:
        text = response['text']
        return json.loads(text)

    return response['text']


class JsonPrompter:
    """
    Adapted from local_llm_function_calling
    """
    def __init__(self, is_instruct: bool = False):
        self.is_instruct = is_instruct

    def function_descriptions(
        self, functions: list[FunctionType], function_to_call: str
    ) -> list[str]:
        """Get the descriptions of the functions

        Args:
            functions (list[FunctionType]): The functions to get the descriptions of
            function_to_call (str): The function to call

        Returns:
            list[str]: The descriptions of the functions
                (empty if the function doesn't exist or has no description)
        """
        return [
            f'# {function["name"]}: {function["description"]}'
            for function in functions
            if function["name"] == function_to_call and "description" in function
        ]

    def function_parameters(
        self, functions: list[FunctionType], function_to_call: str
    ) -> str:
        """Get the parameters of the function

        Args:
            functions (list[FunctionType]): The functions to get the parameters of
            function_to_call (str): The function to call

        Returns:
            str: The parameters of the function as a JSON schema
        """
        return next(
            json.dumps(function["parameters"]["properties"], indent=4)
            for function in functions
            if function["name"] == function_to_call
        )

    def function_data(
        self, functions: list[FunctionType], function_to_call: str
    ) -> str:
        """Get the data for the function

        Args:
            functions (list[FunctionType]): The functions to get the data for
            function_to_call (str): The function to call

        Returns:
            str: The data necessary to generate the arguments for the function
        """
        return "\n".join(
            [
                "Here is the schema for the expected JSON object:",
                "```json",
                self.function_parameters(functions, function_to_call),
                "```",
            ]
        )

    def function_summary(self, function: FunctionType) -> str:
        """Get a summary of a function

        Args:
            function (FunctionType): The function to get the summary of

        Returns:
            str: The summary of the function, as a bullet point
        """
        return f"- {function['name']}" + (
            f" - {function['description']}" if "description" in function else ""
        )

    def functions_summary(self, functions: list[FunctionType]) -> str:
        """Get a summary of the functions

        Args:
            functions (list[FunctionType]): The functions to get the summary of

        Returns:
            str: The summary of the functions, as a bulleted list
        """
        return "Available functions:\n" + "\n".join(
            self.function_summary(function) for function in functions
        )

    def prompt(
        self,
        prompt: str,
        functions: list[FunctionType],
        function_to_call: Union[str, None] = None,
    ) -> str:
        """Generate the llama prompt

        Args:
            prompt (str): The prompt to generate the response to
            functions (list[FunctionType]): The functions to generate the response from
            function_to_call (str | None): The function to call. Defaults to None.

        Returns:
            list[bytes | int]: The llama prompt, a function selection prompt if no
                function is specified, or a function argument prompt if a function is
                specified
        """
        system = (
            "Help choose the appropriate function to call to answer the user's question."
            if function_to_call is None
            else "**IMPORTANT**"
        ) + "\nYou must respond with ONLY the JSON object, with NO additional text or explanation."

        data = (
            self.function_data(functions, function_to_call)
            if function_to_call
            else self.functions_summary(functions)
        )

        if self.is_instruct:
            return f"[INST] <<SYS>>\n{system}\n\n{data}\n<</SYS>>\n\n{prompt} [/INST]"
        else:
            return f"{system}\n\n{data}\n\n{prompt}"
