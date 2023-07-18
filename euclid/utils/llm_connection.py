# llm_connection.py

import re
import requests
from dotenv import load_dotenv
import os
from tiktoken import Tokenizer
from typing import List
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from euclid.const.llm import MIN_TOKENS_FOR_GPT_RESPONSE, MAX_GPT_MODEL_TOKENS
from euclid.const.prompts import SYS_MESSAGE
from jinja2 import Environment, FileSystemLoader

def connect_to_llm():
    pass

def get_user_flows(description):
    prompt = get_prompt('breakdown_1_user_flows.prompt', {'description': description})
    
    messages = [
        SYS_MESSAGE['tdd_engineer'],
        # app type
        # 
        {"role": "user", "content": prompt},
    ]
    
    create_gpt_chat_completion(messages, min_tokens=MIN_TOKENS_FOR_GPT_RESPONSE)


def get_prompt(prompt_name, data):
    # Create a file system loader with the directory of the templates
    file_loader = FileSystemLoader('../prompts')

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

def create_gpt_chat_completion(messages: List[dict], min_tokens=MIN_TOKENS_FOR_GPT_RESPONSE):
    api_key = os.getenv("OPENAI_API_KEY")
    tokens_in_messages = get_tokens_in_messages(messages)
    if tokens_in_messages + min_tokens > MAX_GPT_MODEL_TOKENS:
        raise ValueError(f'Too many tokens in messages: {tokens_in_messages}. Please try a different test.')

    gpt_data = {
        'model': 'gpt-4',
        'n': 1,
        'max_tokens': min(4096, MAX_GPT_MODEL_TOKENS - tokens_in_messages),
        'messages': messages,
        'stream': True
    }

    try:
        return stream_gpt_completion(gpt_data, api_key)
    except Exception as e:
        print('The request to OpenAI API failed. Might be due to GPT being down or due to the too large message. It\'s best if you try another export.')
        print(e)

def stream_gpt_completion(data, api_key):
    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key},
        json=data,
        stream=True
    )

    if response.status_code != 200:
        print(f'problem with request: {response.text}')
        return

    gpt_response = ''
    for line in response.iter_lines():
        if line:  # filter out keep-alive new lines
            json_line = json.loads(line)
            if 'error' in json_line or 'message' in json_line:
                print(json_line, end="")
                return
            content = json_line.get('choices')[0]['message']['content']
            gpt_response += content
            print(content, end="")

    new_code = postprocessing(gpt_response, 'user_flows') # TODO add type dynamically
    return new_code

def postprocessing(gpt_response, type):
    pass