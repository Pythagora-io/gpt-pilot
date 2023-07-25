# prompts/prompts.py
import inquirer
from inquirer.themes import GreenPassion
from termcolor import colored

from const import common
from const.prompts import SYS_MESSAGE
from utils.llm_connection import create_gpt_chat_completion, get_prompt
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

    logger.info('Initial App description done')

    return description


def ask_user(question):
    while True:
        questions = [
            inquirer.Text('answer', message=question)
        ]

        answers = inquirer.prompt(questions, theme=GreenPassion())

        if answers is None:
            print("Exiting application.")
            exit(0)

        if answers['answer'].strip() == '':
            print("No input provided! Please try again.")
            continue
        else:
            return answers['answer']


def get_additional_info_from_openai(messages):
    is_complete = False
    while not is_complete:
        # Obtain clarifications using the OpenAI API
        response = create_gpt_chat_completion(messages, 'additional_info')

        if response is not None:
            # Check if the response is "Thank you!"
            if response.strip() == "Thank you!":
                print(response)
                return messages

            # Ask the question to the user
            answer = ask_user(response)

            # Add the answer to the messages
            messages.append({'role': 'assistant', 'content': response})
            messages.append({'role': 'user', 'content': answer})
        else:
            is_complete = True

    logger.info('Getting additional info done')

    return messages


def generate_messages_from_description(description, app_type):
    prompt = get_prompt('clarification.pt', {'description': description, 'app_type': app_type, 'maximum_questions': 3})

    return [
        SYS_MESSAGE['tdd_engineer'],
        {"role": "user", "content": prompt},
    ]


def execute_chat_prompt(prompt_file, prompt_data, chat_completion_type, print_msg):
    # Generate a prompt for the completion type.
    prompt = get_prompt(prompt_file, prompt_data)

    # Pass the prompt to the API.
    messages = [
        SYS_MESSAGE['tdd_engineer'],
        {"role": "user", "content": prompt},
    ]

    response = create_gpt_chat_completion(messages, chat_completion_type)

    print(colored(f"{print_msg}:\n", "green"))
    print(f"{response}")
    logger.info(f"{print_msg}: {response}")

    return response
