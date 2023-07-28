# prompts/prompts.py
import inquirer
from inquirer.themes import GreenPassion
from termcolor import colored
import questionary

from const import common
from const.llm import MAX_QUESTIONS, END_RESPONSE
from utils.llm_connection import create_gpt_chat_completion, get_prompt
from utils.utils import capitalize_first_word_with_underscores, get_sys_message, find_role_from_step
from logger.logger import logger


def ask_for_app_type():
    questions = [
        inquirer.List('type',
                      message="What type of app do you want to build?",
                      choices=common.APP_TYPES,
                      )
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())
    if answers is None:
        print("Exiting application.")
        exit(0)

    while 'unavailable' in answers['type']:
        print("Sorry, that option is not available.")
        answers = inquirer.prompt(questions, theme=GreenPassion())
        if answers is None:
            print("Exiting application.")
            exit(0)

    print("You chose: " + answers['type'])
    logger.info(f"You chose: {answers['type']}")
    return answers['type']


def ask_for_main_app_definition():
    questions = [
        inquirer.Text('description', message="Describe your app in as many details as possible.")
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())
    if answers is None:
        print("No input provided!")
        return

    description = answers['description']

    while True:
        questions = [
            inquirer.Text('confirmation', message="Do you want to add anything else? If not, just press ENTER.")
        ]

        answers = inquirer.prompt(questions, theme=GreenPassion())
        if answers is None or answers['confirmation'] == '':
            break
        elif description[-1] not in ['.', '!', '?', ';']:
            description += '.'

        description += ' ' + answers['confirmation']

    logger.info(f"Initial App description done: {description}")

    return description


def ask_user(question):
    while True:
        answer = questionary.text(question).ask()

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

    response = create_gpt_chat_completion(messages, chat_type, function_calls=function_calls)

    messages.append({"role": "assistant", "content": response})

    print_msg = capitalize_first_word_with_underscores(chat_type)
    print(colored(f"{print_msg}:\n", "green"))
    print(f"{response}")
    logger.info(f"{print_msg}: {response}\n")

    return response, messages
