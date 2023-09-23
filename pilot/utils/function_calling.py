import json
import re
from typing import Literal, NotRequired, TypedDict, Callable

JsonType = str | int | float | bool | None | list["JsonType"] | dict[str, "JsonType"]


class FunctionParameters(TypedDict):
    """Function parameters"""

    type: Literal["object"]
    properties: dict[str, JsonType]
    required: NotRequired[list[str]]


class FunctionType(TypedDict):
    """Function type"""

    name: str
    description: NotRequired[str]
    parameters: FunctionParameters


class FunctionCall(TypedDict):
    """Function call"""

    name: str
    parameters: str


class FunctionCallSet(TypedDict):
    definitions: list[FunctionType]
    functions: dict[str, Callable]


def add_function_calls_to_request(gpt_data, function_calls: FunctionCallSet | None):
    if function_calls is None:
        return

    model: str = gpt_data['model']
    is_llama = 'llama' in model or 'anthropic' in model

    # if model == 'gpt-4':
    #     gpt_data['functions'] = function_calls['definitions']
    #     if len(function_calls['definitions']) > 1:
    #         gpt_data['function_call'] = 'auto'
    #     else:
    #         gpt_data['function_call'] = {'name': function_calls['definitions'][0]['name']}
    #     return

    prompter = JsonPrompter(is_llama)

    if len(function_calls['definitions']) > 1:
        function_call = None
    else:
        function_call = function_calls['definitions'][0]['name']

    role = 'user' if '/' in model else 'system'

    gpt_data['messages'].append({
        'role': role,
        'content': prompter.prompt('', function_calls['definitions'], function_call)
    })


def parse_agent_response(response, function_calls: FunctionCallSet | None):
    """
    Post-processes the response from the agent.

    Args:
        response: The response from the agent.
        function_calls: Optional function calls associated with the response.

    Returns:
        The post-processed response.
    """

    if function_calls:
        text = re.sub(r'^.*```json\s*', '', response['text'], flags=re.DOTALL)
        values = list(json.loads(text.strip('` \n')).values())
        if len(values) == 1:
            return values[0]
        else:
            return tuple(values)

    return response['text']


class JsonPrompter:
    """
    Adapted from local_llm_function_calling
    """
    def __init__(self, is_llama: bool = False):
        self.is_llama = is_llama

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
            function["description"]
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
            self.function_descriptions(functions, function_to_call)
            + [
                "The response should be a JSON object matching this schema:",
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
        function_to_call: str | None = None,
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
            else f"Define the arguments for {function_to_call} to answer the user's question."
        ) + " \nThe response should contain only the JSON object, with no additional text or explanation."

        data = (
            self.function_data(functions, function_to_call)
            if function_to_call
            else self.functions_summary(functions)
        )
        response_start = (
            f"Here are the arguments for the `{function_to_call}` function: ```json\n"
            if function_to_call
            else "Here's the function the user should call: "
        )

        if self.is_llama:
            return f"[INST] <<SYS>>\n{system}\n\n{data}\n<</SYS>>\n\n{prompt} [/INST]"
        else:
            return f"{system}\n\n{data}\n\n{prompt}"
