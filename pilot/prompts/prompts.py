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
    return 'Web App'
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


def ask_for_main_app_definition(project):
    description = styled_text(
        project,
        "Describe your app in as many details as possible."
    )

    if description is None:
        print("No input provided!")
        return

    logger.info(f"Initial App description done: {description}")

    return description


def ask_user(project, question, require_some_input=True):
    while True:
        answer = styled_text(project, question)

        if answer is None:
            print("Exiting application.")
            exit(0)

        if answer.strip() == '' and require_some_input:
            print("No input provided! Please try again.")
            continue
        else:
            return answer


def get_additional_info_from_openai(project, messages):
    is_complete = False
    while not is_complete:
        # Obtain clarifications using the OpenAI API
        response = create_gpt_chat_completion(messages, 'additional_info')

        if response is not None:
            if response['text'].strip() == END_RESPONSE:
                print(response['text'] + '\n')
                return messages

            # Ask the question to the user
            answer = ask_user(project, response['text'])

            # Add the answer to the messages
            messages.append({'role': 'assistant', 'content': response['text']})
            messages.append({'role': 'user', 'content': answer})
        else:
            is_complete = True

    logger.info('Getting additional info from openai done')

    return messages


# TODO refactor this to comply with AgentConvo class
def get_additional_info_from_user(project,  messages, role):
    # TODO process with agent convo
    updated_messages = []

    for message in messages:

        while True:
            if isinstance(message, dict) and 'text' in message:
                message = message['text']
            print(colored(
                f"Please check this message and say what needs to be changed. If everything is ok just press ENTER",
                "yellow"))
            answer = ask_user(project, message, False)
            if answer.lower() == '':
                break
            response = create_gpt_chat_completion(
                generate_messages_from_custom_conversation(role, [get_prompt('utils/update.prompt'), message, answer], 'user'), 'additional_info')

            message = response

        updated_messages.append(message)

    logger.info('Getting additional info from user done')

    return updated_messages


def generate_messages_from_description(description, app_type, name):
    prompt = get_prompt('high_level_questions/specs.prompt', {
        'name': name,
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
