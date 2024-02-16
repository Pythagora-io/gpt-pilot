import re
import requests
import os
import sys
import time
import json
import tiktoken
from prompt_toolkit.styles import Style

from jsonschema import validate, ValidationError
from utils.style import color_red, color_yellow
from typing import List
from const.llm import MAX_GPT_MODEL_TOKENS, API_CONNECT_TIMEOUT, API_READ_TIMEOUT
from const.messages import AFFIRMATIVE_ANSWERS
from logger.logger import logger, logging
from helpers.exceptions import TokenLimitError, ApiKeyNotDefinedError, ApiError
from utils.utils import fix_json, get_prompt
from utils.function_calling import add_function_calls_to_request, FunctionCallSet, FunctionType
from utils.questionary import styled_text

from .telemetry import telemetry

tokenizer = tiktoken.get_encoding("cl100k_base")


def get_tokens_in_messages(messages: List[str]) -> int:
    tokenized_messages = [tokenizer.encode(message['content']) for message in messages]
    return sum(len(tokens) for tokens in tokenized_messages)


# TODO: not used anywhere
def num_tokens_from_functions(functions):
    """Return the number of tokens used by a list of functions."""
    num_tokens = 0
    for function in functions:
        function_tokens = len(tokenizer.encode(function['name']))
        function_tokens += len(tokenizer.encode(function['description']))

        if 'parameters' in function:
            parameters = function['parameters']
            if 'properties' in parameters:
                for propertiesKey in parameters['properties']:
                    function_tokens += len(tokenizer.encode(propertiesKey))
                    v = parameters['properties'][propertiesKey]
                    for field in v:
                        if field == 'type':
                            function_tokens += 2
                            function_tokens += len(tokenizer.encode(v['type']))
                        elif field == 'description':
                            function_tokens += 2
                            function_tokens += len(tokenizer.encode(v['description']))
                        elif field == 'enum':
                            function_tokens -= 3
                            for o in v['enum']:
                                function_tokens += 3
                                function_tokens += len(tokenizer.encode(o))
                function_tokens += 11

        num_tokens += function_tokens

    num_tokens += 12
    return num_tokens


def test_api_access(project) -> bool:
    """
    Test the API access by sending a request to the API.

    :returns: True if the request was successful, False otherwise.
    """
    messages = [
        {
            "role": "user",
            "content": "This is a connection test. If you can see this, please respond only with 'START' and nothing else."
        }
    ]

    endpoint = os.getenv('ENDPOINT')
    model = os.getenv('MODEL_NAME', 'gpt-4')
    try:
        response = create_gpt_chat_completion(messages, 'project_description', project)
        if response is None or response == {}:
            print(color_red("Error connecting to the API. Please check your API key/endpoint and try again."))
            logger.error(f"The request to {endpoint} model {model} API failed.")
            return False
        return True
    except Exception as err:
        print(color_red("Error connecting to the API. Please check your API key/endpoint and try again."))
        logger.error(f"The request to {endpoint} model {model} API failed: {err}", exc_info=err)
        return False


def create_gpt_chat_completion(messages: List[dict], req_type, project,
                               function_calls: FunctionCallSet = None,
                               prompt_data: dict = None,
                               temperature: float = 0.7):
    """
    Called from:
      - AgentConvo.send_message() - these calls often have `function_calls`, usually from `pilot/const/function_calls.py`
         - convo.continuous_conversation()
    :param messages: [{ "role": "system"|"assistant"|"user", "content": string }, ... ]
    :param req_type: 'project_description' etc. See common.STEPS
    :param project: project
    :param function_calls: (optional) {'definitions': [{ 'name': str }, ...]}
        see `IMPLEMENT_CHANGES` etc. in `pilot/const/function_calls.py`
    :param prompt_data: (optional) { 'prompt': str, 'variables': { 'variable_name': 'variable_value', ... } }
    :return: {'text': new_code}
        or if `function_calls` param provided
             {'function_calls': {'name': str, arguments: {...}}}
    """

    gpt_data = {
        'model': os.getenv('MODEL_NAME', 'gpt-4'),
        'n': 1,
        'temperature': temperature,
        'top_p': 1,
        'presence_penalty': 0,
        'frequency_penalty': 0,
        'messages': messages,
        'stream': True
    }

    # delete some keys if using "OpenRouter" API
    if os.getenv('ENDPOINT') == 'OPENROUTER':
        keys_to_delete = ['n', 'max_tokens', 'temperature', 'top_p', 'presence_penalty', 'frequency_penalty']
        for key in keys_to_delete:
            if key in gpt_data:
                del gpt_data[key]

    # Advise the LLM of the JSON response schema we are expecting
    messages_length = len(messages)
    function_call_message = add_function_calls_to_request(gpt_data, function_calls)
    if prompt_data is not None and function_call_message is not None:
        prompt_data['function_call_message'] = function_call_message

    try:
        response = stream_gpt_completion(gpt_data, req_type, project)

        # Remove JSON schema and any added retry messages
        while len(messages) > messages_length:
            messages.pop()
        return response
    except TokenLimitError as e:
        raise e
    except Exception as e:
        logger.error(f'The request to {os.getenv("ENDPOINT")} API failed: %s', e)
        print(color_red(f'The request to {os.getenv("ENDPOINT")} API failed with error: {e}. Please try again later.'))
        if isinstance(e, ApiError):
            raise e
        else:
            raise ApiError(f"Error making LLM API request: {e}") from e

def delete_last_n_lines(n):
    for _ in range(n):
        # Move the cursor up one line
        sys.stdout.write('\033[F')
        # Clear the current line
        sys.stdout.write('\033[K')


def count_lines_based_on_width(content, width):
    lines_required = sum(len(line) // width + 1 for line in content.split('\n'))
    return lines_required


def get_tokens_in_messages_from_openai_error(error_message):
    """
    Extract the token count from a message.

    Args:
    message (str): The message to extract the token count from.

    Returns:
    int or None: The token count if found, otherwise None.
    """

    match = re.search(r"your messages resulted in (\d+) tokens", error_message)
    if match:
        return int(match.group(1))

    match = re.search(r"Requested (\d+). The input or output tokens must be reduced", error_message)
    if match:
        return int(match.group(1))

    return None


def retry_on_exception(func):
    def update_error_count(args):
        function_error_count = 1 if 'function_error' not in args[0] else args[0]['function_error_count'] + 1
        args[0]['function_error_count'] = function_error_count
        return function_error_count

    def set_function_error(args, err_str: str):
        logger.info(err_str)

        args[0]['function_error'] = err_str
        if 'function_buffer' in args[0]:
            del args[0]['function_buffer']

    def wrapper(*args, **kwargs):
        while True:
            try:
                # spinner_stop(spinner)
                return func(*args, **kwargs)
            except Exception as e:
                # Convert exception to string
                err_str = str(e)

                if isinstance(e, json.JSONDecodeError):
                    # codellama-34b-instruct seems to send incomplete JSON responses.
                    # We ask for the rest of the JSON object for the following errors:
                    # - 'Expecting value' (error if `e.pos` not at the end of the doc: True instead of true)
                    # - "Expecting ':' delimiter"
                    # - 'Expecting property name enclosed in double quotes'
                    # - 'Unterminated string starting at'
                    if e.msg.startswith('Expecting') or e.msg == 'Unterminated string starting at':
                        if e.msg == 'Expecting value' and len(e.doc) > e.pos:
                            # Note: clean_json_response() should heal True/False boolean values
                            err_str = re.split(r'[},\\n]', e.doc[e.pos:])[0]
                            err_str = f'Invalid value: `{err_str}`'
                        else:
                            # if e.msg == 'Unterminated string starting at' or len(e.doc) == e.pos:
                            logger.info('Received incomplete JSON response from LLM. Asking for the rest...')
                            args[0]['function_buffer'] = e.doc
                            if 'function_error' in args[0]:
                                del args[0]['function_error']
                            continue

                    # TODO: (if it ever comes up) e.msg == 'Extra data' -> trim the response
                    # 'Invalid control character at', 'Invalid \\escape', 'Invalid control character',
                    # or `Expecting value` with `pos` before the end of `e.doc`
                    function_error_count = update_error_count(args)
                    logger.warning('Received invalid character in JSON response from LLM. Asking to retry...')
                    logger.info(f'  received: {e.doc}')
                    set_function_error(args, err_str)
                    if function_error_count < 3:
                        continue
                elif isinstance(e, ValidationError):
                    function_error_count = update_error_count(args)
                    logger.warning('Received invalid JSON response from LLM. Asking to retry...')
                    # eg:
                    # json_path: '$.type'
                    # message:   "'command' is not one of ['automated_test', 'command_test', 'manual_test', 'no_test']"
                    set_function_error(args, f'at {e.json_path} - {e.message}')
                    # Attempt retry if the JSON schema is invalid, but avoid getting stuck in a loop
                    if function_error_count < 3:
                        continue
                if "context_length_exceeded" in err_str or "Request too large" in err_str:
                    # If the specific error "context_length_exceeded" is present, simply return without retry
                    # spinner_stop(spinner)
                    n_tokens = get_tokens_in_messages_from_openai_error(err_str)
                    print(color_red(f"Error calling LLM API: The request exceeded the maximum token limit (request size: {n_tokens}) tokens."))
                    trace_token_limit_error(n_tokens, args[0]['messages'], err_str)
                    raise TokenLimitError(n_tokens, MAX_GPT_MODEL_TOKENS)
                if "rate_limit_exceeded" in err_str:
                    rate_limit_exceeded_sleep(e, err_str)
                    continue

                print(color_red('There was a problem with request to openai API:'))
                # spinner_stop(spinner)
                print(err_str)
                logger.error(f'There was a problem with request to openai API: {err_str}')

                project = args[2]
                print('yes/no', type='buttons-only')
                user_message = styled_text(
                    project,
                    'Do you want to try make the same request again? If yes, just press ENTER. Otherwise, type "no".',
                    style=Style.from_dict({
                        'question': '#FF0000 bold',
                        'answer': '#FF910A bold'
                    })
                )

                # TODO: take user's input into consideration - send to LLM?
                # https://github.com/Pythagora-io/gpt-pilot/issues/122
                if user_message.lower() not in AFFIRMATIVE_ANSWERS:
                    if isinstance(e, ApiError):
                        raise
                    else:
                        raise ApiError(f"Error making LLM API request: {err_str}") from e

    return wrapper


def rate_limit_exceeded_sleep(e, err_str):
    extra_buffer_time = float(os.getenv('RATE_LIMIT_EXTRA_BUFFER', 6))  # extra buffer time to wait, defaults to 6 secs
    wait_duration_sec = extra_buffer_time  # Default time to wait in seconds

    # Regular expression to find milliseconds
    match = re.search(r'Please try again in (\d+)ms.', err_str)
    if match:
        milliseconds = int(match.group(1))
        wait_duration_sec += milliseconds / 1000
    else:
        # Regular expression to find minutes and seconds
        match = re.search(r'Please try again in (\d+)m(\d+\.\d+)s.', err_str)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            wait_duration_sec += minutes * 60 + seconds
        else:
            # Check for only seconds
            match = re.search(r'(\d+\.\d+)s.', err_str)
            if match:
                seconds = float(match.group(1))
                wait_duration_sec += seconds

    logger.debug(f'Rate limited. Waiting {wait_duration_sec} seconds...')

    if isinstance(e, ApiError) and hasattr(e, "response_json") and e.response_json is not None and "error" in e.response_json:
        message = e.response_json["error"]["message"]
    else:
        message = "Rate limited by the API (we're over 'tokens per minute' or 'requests per minute' limit)"
    print(color_yellow(message))
    print(color_yellow(f"Retrying in {wait_duration_sec} second(s)... with extra buffer of: {extra_buffer_time} second(s)"))
    time.sleep(wait_duration_sec)


def trace_token_limit_error(request_tokens: int, messages: list[dict], err_str: str):
    # This must match files_list.prompt format in order to be able to count number of sent files
    FILES_SECTION_PATTERN = r".*---START_OF_FILES---(.*)---END_OF_FILES---"
    FILE_PATH_PATTERN = r"^\*\*(.*?)\*\*.*:$"

    sent_files = set()
    for msg in messages:
        if not msg.get("content"):
            continue
        m = re.match(FILES_SECTION_PATTERN, msg["content"], re.DOTALL)
        if not m:
            continue
        files_section = m.group(1)
        msg_files = re.findall(FILE_PATH_PATTERN, files_section, re.MULTILINE)
        sent_files.update(msg_files)

    # Importing here to avoid circular import problem
    from utils.exit import trace_code_event
    trace_code_event(
        "llm-request-token-limit-error",
        {
            "n_messages": len(messages),
            "n_tokens": request_tokens,
            "files": sorted(sent_files),
            "error": err_str,
        }
    )


@retry_on_exception
def stream_gpt_completion(data, req_type, project):
    """
    Called from create_gpt_chat_completion()
    :param data:
    :param req_type: 'project_description' etc. See common.STEPS
    :param project: NEEDED FOR WRAPPER FUNCTION retry_on_exception
    :return: {'text': str} or {'function_calls': {'name': str, arguments: '{...}'}}
    """
    # TODO add type dynamically - this isn't working when connected to the external process
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 50
    lines_printed = 2
    gpt_response = ''
    buffer = ''  # A buffer to accumulate incoming data
    expecting_json = None
    received_json = False

    if 'functions' in data:
        expecting_json = data['functions']
        if 'function_buffer' in data:
            incomplete_json = get_prompt('utils/incomplete_json.prompt', {'received_json': data['function_buffer']})
            data['messages'].append({'role': 'user', 'content': incomplete_json})
            gpt_response = data['function_buffer']
            received_json = True
        elif 'function_error' in data:
            invalid_json = get_prompt('utils/invalid_json.prompt', {'invalid_reason': data['function_error']})
            data['messages'].append({'role': 'user', 'content': invalid_json})
            received_json = True

        # Don't send the `functions` parameter to Open AI, but don't remove it from `data` in case we need to retry
        data = {key: value for key, value in data.items() if not key.startswith('function')}

    def return_result(result_data, lines_printed):
        if buffer:
            lines_printed += count_lines_based_on_width(buffer, terminal_width)
        logger.debug(f'lines printed: {lines_printed} - {terminal_width}')

        # delete_last_n_lines(lines_printed)  # TODO fix and test count_lines_based_on_width()
        return result_data

    # spinner = spinner_start(yellow("Waiting for OpenAI API response..."))
    # print(yellow("Stream response from OpenAI:"))

    # Configure for the selected ENDPOINT
    model = os.getenv('MODEL_NAME', 'gpt-4')
    endpoint = os.getenv('ENDPOINT')

    logger.info(f'> Request model: {model}')
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('\n'.join([f"{message['role']}: {message['content']}" for message in data['messages']]))

    if endpoint == 'AZURE':
        # If yes, get the AZURE_ENDPOINT from .ENV file
        endpoint_url = os.getenv('AZURE_ENDPOINT') + '/openai/deployments/' + model + '/chat/completions?api-version=2023-05-15'
        headers = {
            'Content-Type': 'application/json',
            'api-key': get_api_key_or_throw('AZURE_API_KEY')
        }
    elif endpoint == 'OPENROUTER':
        # If so, send the request to the OpenRouter API endpoint
        endpoint_url = os.getenv('OPENROUTER_ENDPOINT', 'https://openrouter.ai/api/v1/chat/completions')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + get_api_key_or_throw('OPENROUTER_API_KEY'),
            'HTTP-Referer': 'https://github.com/Pythagora-io/gpt-pilot',
            'X-Title': 'GPT Pilot'
        }
        data['max_tokens'] = MAX_GPT_MODEL_TOKENS
        data['model'] = model
    else:
        # If not, send the request to the OpenAI endpoint
        endpoint_url = os.getenv('OPENAI_ENDPOINT', 'https://api.openai.com/v1/chat/completions')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + get_api_key_or_throw('OPENAI_API_KEY')
        }
        data['model'] = model

    telemetry.set("model", model)
    token_count = get_tokens_in_messages(data['messages'])
    request_start_time = time.time()

    response = requests.post(
        endpoint_url,
        headers=headers,
        json=data,
        stream=True,
        timeout=(API_CONNECT_TIMEOUT, API_READ_TIMEOUT),
    )

    if response.status_code != 200:
        project.dot_pilot_gpt.log_chat_completion(endpoint, model, req_type, data['messages'], response.text)
        logger.info(f'problem with request (status {response.status_code}): {response.text}')
        telemetry.record_llm_request(token_count, time.time() - request_start_time, is_error=True)
        raise ApiError(f"API responded with status code: {response.status_code}. Request token size: {token_count} tokens. Response text: {response.text}", response=response)

    # function_calls = {'name': '', 'arguments': ''}

    for line in response.iter_lines():
        # Ignore keep-alive new lines
        if line and line != b': OPENROUTER PROCESSING':
            line = line.decode("utf-8")  # decode the bytes to string

            if line.startswith('data: '):
                line = line[6:]  # remove the 'data: ' prefix

            # Check if the line is "[DONE]" before trying to parse it as JSON
            if line == "[DONE]":
                continue

            try:
                json_line = json.loads(line)

                if len(json_line['choices']) == 0:
                    continue

                if 'error' in json_line:
                    logger.error(f'Error in LLM response: {json_line}')
                    telemetry.record_llm_request(token_count, time.time() - request_start_time, is_error=True)
                    raise ValueError(f'Error in LLM response: {json_line["error"]["message"]}')

                choice = json_line['choices'][0]

                # if 'finish_reason' in choice and choice['finish_reason'] == 'function_call':
                #     function_calls['arguments'] = load_data_to_json(function_calls['arguments'])
                #     return return_result({'function_calls': function_calls}, lines_printed)

                json_line = choice['delta']

            except json.JSONDecodeError as e:
                logger.error(f'Unable to decode line: {line} {e.msg}')
                continue  # skip to the next line

            # handle the streaming response
            # if 'function_call' in json_line:
            #     if 'name' in json_line['function_call']:
            #         function_calls['name'] = json_line['function_call']['name']
            #         print(f'Function call: {function_calls["name"]}')
            #
            #     if 'arguments' in json_line['function_call']:
            #         function_calls['arguments'] += json_line['function_call']['arguments']
            #         print(json_line['function_call']['arguments'], type='stream', end='', flush=True)

            if 'content' in json_line:
                content = json_line.get('content')
                if content:
                    buffer += content  # accumulate the data

                    # If you detect a natural breakpoint (e.g., line break or end of a response object), print & count:
                    if buffer.endswith('\n'):
                        if expecting_json and not received_json:
                            try:
                                received_json = assert_json_response(buffer, lines_printed > 2)
                            except:
                                telemetry.record_llm_request(token_count, time.time() - request_start_time, is_error=True)
                                raise
                        # or some other condition that denotes a breakpoint
                        lines_printed += count_lines_based_on_width(buffer, terminal_width)
                        buffer = ""  # reset the buffer

                    gpt_response += content
                    print(content, type='stream', end='', flush=True)

    print('\n', type='stream')

    telemetry.record_llm_request(
        token_count + len(tokenizer.encode(gpt_response)),
        time.time() - request_start_time,
        is_error=False
    )

    # if function_calls['arguments'] != '':
    #     logger.info(f'Response via function call: {function_calls["arguments"]}')
    #     function_calls['arguments'] = load_data_to_json(function_calls['arguments'])
    #     return return_result({'function_calls': function_calls}, lines_printed)
    logger.info('<<<<<<<<<< LLM Response <<<<<<<<<<\n%s\n<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<', gpt_response)
    project.dot_pilot_gpt.log_chat_completion(endpoint, model, req_type, data['messages'], gpt_response)

    if expecting_json:
        gpt_response = clean_json_response(gpt_response)
        assert_json_schema(gpt_response, expecting_json)
        # Note, we log JSON separately from the YAML log above incase the JSON is invalid and an error is raised
        project.dot_pilot_gpt.log_chat_completion_json(endpoint, model, req_type, expecting_json, gpt_response)

    new_code = postprocessing(gpt_response, req_type)  # TODO add type dynamically
    return return_result({'text': new_code}, lines_printed)


def get_api_key_or_throw(env_key: str):
    api_key = os.getenv(env_key)
    if api_key is None:
        raise ApiKeyNotDefinedError(env_key)
    return api_key


def assert_json_response(response: str, or_fail=True) -> bool:
    if re.match(r'.*(```(json)?|{|\[)', response):
        return True
    elif or_fail:
        logger.error(f'LLM did not respond with JSON: {response}')
        raise ValueError('LLM did not respond with JSON')
    else:
        return False


def clean_json_response(response: str) -> str:
    response = re.sub(r'^.*```json\s*', '', response, flags=re.DOTALL)
    response = re.sub(r': ?True(,)?$', r':true\1', response, flags=re.MULTILINE)
    response = re.sub(r': ?False(,)?$', r':false\1', response, flags=re.MULTILINE)
    return response.strip('` \n')


def assert_json_schema(response: str, functions: list[FunctionType]) -> True:
    for function in functions:
        schema = function['parameters']
        parsed = json.loads(response)
        validate(parsed, schema)
        return True


def postprocessing(gpt_response: str, req_type) -> str:
    return gpt_response


def load_data_to_json(string):
    return json.loads(fix_json(string))
