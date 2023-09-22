from local_llm_function_calling.prompter import CompletionModelPrompter, InstructModelPrompter

from const.function_calls import ARCHITECTURE, DEV_STEPS
from .function_calling import JsonPrompter


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
        "description": "List of technologies that are created in a list.",
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
        "description": "List of technologies that are created in a list.",
        "items": {
            "type": "string",
            "description": "technology"
        }
    }
}
```

Create a web-based chat app

Function call: '''


def test_json_prompter():
    # Given
    prompter = JsonPrompter()

    # When
    prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'])  # , 'process_technologies')

    # Then
    assert prompt == '''[INST] <<SYS>>
Help choose the appropriate function to call to answer the user's question.
In your response you must only use JSON output and provide no notes or commentary.

Available functions:
- process_technologies - Print the list of technologies that are created.
<</SYS>>

Create a web-based chat app [/INST]'''


def test_llama_instruct_function_prompter_named():
    # Given
    prompter = LlamaInstructPrompter()

    # When
    prompt = prompter.prompt('Create a web-based chat app', ARCHITECTURE['definitions'], 'process_technologies')

    # Then
    assert prompt == '''[INST] <<SYS>>
Define the arguments for process_technologies to answer the user's question.
In your response you must only use JSON output and provide no notes or commentary.

Function description: Print the list of technologies that are created.
Function parameters should follow this schema:
```jsonschema
{
    "technologies": {
        "type": "array",
        "description": "List of technologies that are created in a list.",
        "items": {
            "type": "string",
            "description": "technology"
        }
    }
}
```
<</SYS>>

Create a web-based chat app [/INST]'''
