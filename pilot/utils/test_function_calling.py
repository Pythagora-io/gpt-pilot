from local_llm_function_calling.prompter import CompletionModelPrompter, InstructModelPrompter

from const.function_calls import ARCHITECTURE, DEV_STEPS
from .function_calling import parse_agent_response, JsonPrompter


class TestFunctionCalling:
    def test_parse_agent_response_text(self):
        # Given
        response = {'text': 'Hello world!'}

        # When
        response = parse_agent_response(response, None)

        # Then
        assert response == 'Hello world!'

    def test_parse_agent_response_json(self):
        # Given
        response = {'text': '{"greeting": "Hello world!"}'}
        function_calls = {'definitions': [], 'functions': {}}

        # When
        response = parse_agent_response(response, function_calls)

        # Then
        assert response == 'Hello world!'

    def test_parse_agent_response_json_markdown(self):
        # Given
        response = {'text': '```json\n{"greeting": "Hello world!"}\n```'}
        function_calls = {'definitions': [], 'functions': {}}

        # When
        response = parse_agent_response(response, function_calls)

        # Then
        assert response == 'Hello world!'

    def test_parse_agent_response_markdown(self):
        # Given
        response = {'text': '```\n{"greeting": "Hello world!"}\n```'}
        function_calls = {'definitions': [], 'functions': {}}

        # When
        response = parse_agent_response(response, function_calls)

        # Then
        assert response == 'Hello world!'

    def test_parse_agent_response_multiple_args(self):
        # Given
        response = {'text': '{"greeting": "Hello", "name": "John"}'}
        function_calls = {'definitions': [], 'functions': {}}

        # When
        greeting, name = parse_agent_response(response, function_calls)

        # Then
        assert greeting == 'Hello'
        assert name == 'John'


def test_completion_function_prompt():
    # Given
    prompter = CompletionModelPrompter()

    # When
    prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'])  # , 'process_technologies')

    # Then
    assert prompt == '''Create a web-based chat app

Available functions:
process_technologies - Print the list of technologies that are created.
```jsonschema
{
    "technologies": {
        "type": "array",
        "description": "List of technologies.",
        "items": {
            "type": "string",
            "description": "technology"
        }
    }
}
```

Function call: 

Function call: '''


def test_instruct_function_prompter():
    # Given
    prompter = InstructModelPrompter()

    # When
    prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'])  # , 'process_technologies')

    # Then
    assert prompt == '''Your task is to call a function when needed. You will be provided with a list of functions. Available functions:
process_technologies - Print the list of technologies that are created.
```jsonschema
{
    "technologies": {
        "type": "array",
        "description": "List of technologies.",
        "items": {
            "type": "string",
            "description": "technology"
        }
    }
}
```

Create a web-based chat app

Function call: '''


# def test_json_prompter():
#     # Given
#     prompter = JsonPrompter()
#
#     # When
#     prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'])  # , 'process_technologies')
#
#     # Then
#     assert prompt == '''[INST] <<SYS>>
# Help choose the appropriate function to call to answer the user's question.
# In your response you must only use JSON output and provide no notes or commentary.
#
# Available functions:
# - process_technologies - Print the list of technologies that are created.
# <</SYS>>
#
# Create a web-based chat app [/INST]'''


def test_json_prompter_named():
    # Given
    prompter = JsonPrompter()

    # When
    prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'], 'process_technologies')

    # Then
    assert prompt == '''Define the arguments for process_technologies to answer the user's question.
The response should contain only the JSON object, with no additional text or explanation.

Print the list of technologies that are created.
The response should be a JSON object matching this schema:
```json
{
    "technologies": {
        "type": "array",
        "description": "List of technologies.",
        "items": {
            "type": "string",
            "description": "technology"
        }
    }
}
```

Create a web-based chat app'''


def test_llama_json_prompter_named():
    # Given
    prompter = JsonPrompter(is_llama=True)

    # When
    prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'], 'process_technologies')

    # Then
    assert prompt == '''[INST] <<SYS>>
Define the arguments for process_technologies to answer the user's question.
The response should contain only the JSON object, with no additional text or explanation.

Print the list of technologies that are created.
The response should be a JSON object matching this schema:
```json
{
    "technologies": {
        "type": "array",
        "description": "List of technologies.",
        "items": {
            "type": "string",
            "description": "technology"
        }
    }
}
```
<</SYS>>

Create a web-based chat app [/INST]'''
