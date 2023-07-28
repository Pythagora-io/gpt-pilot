# llm_connection_old.py
import requests
import os
import json
# from tiktoken import Tokenizer
from typing import List
from jinja2 import Environment, FileSystemLoader

from const.llm import MIN_TOKENS_FOR_GPT_RESPONSE, MAX_GPT_MODEL_TOKENS, MAX_QUESTIONS, END_RESPONSE
from logger.logger import logger
from termcolor import colored
from utils.utils import get_prompt_components


def connect_to_llm():
    pass


def get_prompt(prompt_name, data=None):
    if data is None:
        data = {}

    data.update(get_prompt_components())

    logger.debug(f"Getting prompt for {prompt_name}")  # logging here
    # Create a file system loader with the directory of the templates
    file_loader = FileSystemLoader('prompts')

    # Create the Jinja2 environment
    env = Environment(loader=file_loader)

    # Load the template
    template = env.get_template(prompt_name)

    # Render the template with the provided data
    output = template.render(data)

    return output


def get_tokens_in_messages(messages: List[str]) -> int:
    tokenizer = Tokenizer()
    tokenized_messages = [tokenizer.encode(message) for message in messages]
    return sum(len(tokens) for tokens in tokenized_messages)


def create_gpt_chat_completion(messages: List[dict], req_type, min_tokens=MIN_TOKENS_FOR_GPT_RESPONSE, function_calls=None):
    api_key = os.getenv("OPENAI_API_KEY")
    #     tokens_in_messages = get_tokens_in_messages(messages)
    tokens_in_messages = 100
    if tokens_in_messages + min_tokens > MAX_GPT_MODEL_TOKENS:
        raise ValueError(f'Too many tokens in messages: {tokens_in_messages}. Please try a different test.')

    gpt_data = {
        'model': 'gpt-4',
        'n': 1,
        'max_tokens': min(4096, MAX_GPT_MODEL_TOKENS - tokens_in_messages),
        'messages': messages,
        'stream': True
    }

    if function_calls is not None:
        gpt_data['functions'] = function_calls['definitions']
        gpt_data['function_call'] = "auto"

    try:
        response = stream_gpt_completion(gpt_data, req_type)
        if 'function_calls' in response and function_calls is not None:
            function_calls['callback'](response['function_calls']);
        elif 'text' in response:
            return response['text']
    except Exception as e:
        print(
            'The request to OpenAI API failed. Might be due to GPT being down or due to the too large message. It\'s '
            'best if you try again.')
        print(e)


def stream_gpt_completion(data, req_type):
    print(colored("Waiting for OpenAI API response...", 'light_magenta'))
    api_key = os.getenv("OPENAI_API_KEY")

    logger.info(f'Request data: {data}')

    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key},
        json=data,
        stream=True
    )

    # Log the response status code and message
    logger.info(f'Response status code: {response.status_code}')

    if response.status_code != 200:
        print(f'problem with request: {response.text}')
        logger.debug(f'problem with request: {response.text}')
        return {}

    gpt_response = ''
    function_calls = { 'name': '', 'arguments': '' }

    for line in response.iter_lines():
        # Ignore keep-alive new lines
        if line:
            line = line.decode("utf-8")  # decode the bytes to string

            if line.startswith('data: '):
                line = line[6:]  # remove the 'data: ' prefix

            # Check if the line is "[DONE]" before trying to parse it as JSON
            if line == "[DONE]":
                continue

            try:
                json_line = json.loads(line)
                if json_line['choices'][0]['finish_reason'] == 'function_call':
                    function_calls['arguments'] = json.loads(function_calls['arguments'])
                    return { 'function_calls': function_calls };

                json_line = json_line['choices'][0]['delta']
            except json.JSONDecodeError:
                logger.error(f'Unable to decode line: {line}')
                continue  # skip to the next line

            if 'function_call' in json_line:
                if 'name' in json_line['function_call']:
                    function_calls['name'] = json_line['function_call']['name']
                if 'arguments' in json_line['function_call']:
                    function_calls['arguments'] += json_line['function_call']['arguments']
            if 'content' in json_line:
                content = json_line.get('content')
                if content:
                    gpt_response += content

    logger.info(f'Response message: {gpt_response}')
    new_code = postprocessing(gpt_response, req_type)  # TODO add type dynamically
    return { 'text': new_code }


def postprocessing(gpt_response, req_type):
    return gpt_response
