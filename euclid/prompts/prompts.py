# prompts/prompts.py

from termcolor import colored
import questionary

from const import common
from const.llm import MAX_QUESTIONS, END_RESPONSE
from utils.llm_connection import create_gpt_chat_completion, get_prompt
from utils.utils import capitalize_first_word_with_underscores, get_sys_message, find_role_from_step
from utils.questionary import styled_select, styled_text
from logger.logger import logger


def ask_for_app_type():
    answer = styled_select(
        "What type of app do you want to build?",
        choices=common.APP_TYPES
    )

    if answer is None:
        print("Exiting application.")
        exit(0)

    while 'unavailable' in answer:
        print("Sorry, that option is not available.")
        answer = styled_select(
            "What type of app do you want to build?",
            choices=common.APP_TYPES
        )
        if answer is None:
            print("Exiting application.")
            exit(0)

    print("You chose: " + answer)
    logger.info(f"You chose: {answer}")
    return answer


def ask_for_main_app_definition():
    description = styled_text(
        "Describe your app in as many details as possible."
    )

    if description is None:
        print("No input provided!")
        return

    while True:
        confirmation = styled_text(
            "Do you want to add anything else? If not, just press ENTER."
        )

        if confirmation is None or confirmation == '':
            break
        elif description[-1] not in ['.', '!', '?', ';']:
            description += '.'

        description += ' ' + confirmation

    logger.info(f"Initial App description done: {description}")

    return description


def ask_user(question):
    while True:
        answer = styled_text(question)

        if answer is None:
            print("Exiting application.")
            exit(0)

        if answer.strip() == '':
            print("No input provided! Please try again.")
            continue
        else:
            return answer


def get_additional_info_from_openai(messages):
    is_complete = False
    while not is_complete:
        # Obtain clarifications using the OpenAI API
        response = create_gpt_chat_completion(messages, 'additional_info')

        if response is not None:
            if response.strip() == END_RESPONSE:
                print(response)
                return messages

            # Ask the question to the user
            answer = ask_user(response)

            # Add the answer to the messages
            messages.append({'role': 'assistant', 'content': response})
            messages.append({'role': 'user', 'content': answer})
        else:
            is_complete = True

    logger.info('Getting additional info from openai done')

    return messages


def get_additional_info_from_user(messages, role):
    updated_messages = []

    for message in messages:

        while True:
            print(colored(
                f"Please check this message and say what needs to be changed. If everything is ok just type 'DONE'.",
                "yellow"))
            answer = ask_user(message)
            if answer.lower() == 'done':
                break
            response = create_gpt_chat_completion(
                generate_messages_from_custom_conversation(role, [get_prompt('utils/update.prompt'), message, answer],
                                                           'user'),
                'additional_info')

            message = response

        updated_messages.append(message)

    logger.info('Getting additional info from user done')

    return "\n\n".join(updated_messages)


def generate_messages_from_description(description, app_type):
    prompt = get_prompt('high_level_questions/specs.prompt', {
        'prompt': description,
        'app_type': app_type,
        'MAX_QUESTIONS': MAX_QUESTIONS
    })

    return [
        get_sys_message('product_owner'),
        {"role": "user", "content": prompt},
    ]


def generate_messages_from_custom_conversation(role, messages, start_role='user'):
    # messages is list of strings
    result = [get_sys_message(role)]

    for i, message in enumerate(messages):
        if i % 2 == 0:
            result.append({"role": start_role, "content": message})
        else:
            result.append({"role": "assistant" if start_role == "user" else "user", "content": message})

    return result


def execute_chat_prompt(prompt_file, prompt_data, chat_type, previous_messages=None, function_calls=None):
    # Generate a prompt for the completion type.
    prompt = get_prompt(prompt_file, prompt_data)
    new_message = {"role": "user", "content": prompt}

    if previous_messages:
        # Use the provided previous_messages instead of the default system message.
        messages = previous_messages + [new_message]
    else:
        # Use the default system message.
        messages = [
            get_sys_message(find_role_from_step(chat_type)),
            new_message,
        ]

    # TODO remove this once the database is set up properly
    for message in messages:
        if isinstance(message['content'], list):
            message['content'] = '\n'.join(message['content'])
        else:
            message['content'] = str(message['content'])
    # TODO END

    response = create_gpt_chat_completion(messages, chat_type, function_calls=function_calls)

    # TODO we need to specify the response when there is a function called
    # TODO maybe we can have a specific function that creates the GPT response from the function call
    messages.append({"role": "assistant", "content": response['text'] if 'text' in response else str(response['function_calls']['name'])})
    print_msg = capitalize_first_word_with_underscores(chat_type)
    print(colored(f"{print_msg}:\n", "green"))
    print(f"{response}")
    logger.info(f"{print_msg}: {response}\n")
    
    if 'function_calls' in response and function_calls is not None:
        if 'send_messages_and_step' in function_calls:
            response['function_calls']['arguments']['previous_messages']  = messages
            response['function_calls']['arguments']['current_step'] = chat_type
        response, msgs = function_calls['functions'][response['function_calls']['name']](**response['function_calls']['arguments'])
        if msgs is not None:
            messages = msgs
    elif 'text' in response:
        response = response['text']

    return response, messages
