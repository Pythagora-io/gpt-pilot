import os
import time
import json

from logger.logger import logger
from utils.llm_connection import create_gpt_chat_completion
from const.function_calls import DESCRIBE_FILE


DESCRIBE_PROMPT = """You're a software developer AI assistant. Your task is to explain the functionality implemented by a particular source code file.

Given a file path and file contents, your output should contain:

* a short explanation of what the file is about;
* a list of all other files referenced (imported) from this file. note that some libraries, frameworks or libraries assume file extension and don't use it explicitly. For example, "import foo" in Python references "foo.py" without specifying the extension. In your response, use the complete file name including the implied extension;

Output the result in a JSON format with the following structure, as in this example:

Example:
{
    "summary": "Describe in detail the functionality being defind o implemented in this file. Be as detailed as possible",
    "references": [
        "some/file.py",
        "some/other/file.js"
    ],
}

Your response must be a valid JSON document, following the example format. Do not add any extra explanation or commentary outside the JSON document.
"""

def _get_describe_messages(fpath: str, content: str) -> list[dict[str, str]]:
    """
    Return a list of messages to send to the AI model to describe a file.

    Internal to this module, use `describe_file` instead.

    :param fpath: the file path
    :param content: the file content
    :return: a list of messages
    """
    return [
        {"role": "system", "content": DESCRIBE_PROMPT},
        {"role": "user", "content": f"Here's the `{fpath}` file:\n```\n{content}\n```\n"},
    ]


def describe_file(project, fpath: str, content: str) -> str:
    if os.getenv('FILTER_RELEVANT_FILES', '').lower().strip() in ['false', '0', 'no', 'off']:
        return ''

    model_name = os.getenv("MODEL_NAME")
    if model_name.startswith("gpt-4") or model_name.startswith("openai/gpt-4"):
        model_name = "gpt-3.5-turbo"
    elif model_name.startswith("claude-3") or model_name.startswith("anthropic/claude-3"):
        model_name = "anthropic/claude-3-haiku-20240307"
    else:
        # Unknown default model (possibly local LLM), didsable file summaries
        return ''

    if not content or not content.strip():
        return "(empty)"

    logger.info("Calling %s to summarize file %s", model_name, fpath)
    try:
        response_text = create_gpt_chat_completion(
            _get_describe_messages(fpath, content),
            'project_description',
            project,
            function_calls=DESCRIBE_FILE,
            temperature=0,
            model_name=model_name,
        )
        response = json.loads(response_text['text'])
        refs = (" [References: " + ", ".join(response["references"]) + "]") if response.get("references") else ""
        return f"{response['summary']}{refs}"
    except Exception as err:
        logger.error("Error summarizing %s: %s", fpath, err, exc_info=True)
        return '(unknown)'
