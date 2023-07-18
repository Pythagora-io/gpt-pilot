# main.py

from __future__ import print_function, unicode_literals
from euclid.const import common
from euclid.utils import llm_connection
import inquirer
import uuid
from inquirer.themes import GreenPassion
from euclid.database import save_progress, save_app

def break_down_user_flows(description):
    user_flows = parse_description_into_user_flows(description)
    for flow_index, user_flow in enumerate(user_flows):
        is_correct = False
        while not is_correct:
            print(f"User Flow {flow_index+1}: {user_flow}")
            is_correct = ask_for_user_flow_confirmation(flow_index)
        save_progress(app_id, f'user_flow_{flow_index+1}', user_flow)

def ask_for_user_flow_confirmation(flow_index):
    questions = [
        inquirer.List('confirmation',
            message=f"Does user flow {flow_index+1} meet your requirements? (Yes/No)",
            choices=['Yes', 'No'],
        )
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    if answers is None:
        print("No input provided!")
        return
    
    if answers['confirmation'] == 'Yes':
        return True
    else:
        return modify_user_flow(flow_index)

def modify_user_flow(flow_index):
    questions = [
        inquirer.Text('correction', message=f"Please provide corrections for user flow {flow_index+1}.")
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())
    user_flows[flow_index] = answers['correction']
    return False

def ask_for_app_type():
    questions = [
        inquirer.List('type',
            message="What type of app do you want to build?",
            choices=common.APP_TYPES,
        )
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())

    while answers is None or 'unavailable' in answers['type']:
        if answers is None:
            print("You need to make a selection.")
        else:
            print("Sorry, that option is not available.")

        answers = inquirer.prompt(questions, theme=GreenPassion())

    print("You chose: " + answers['type'])
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

    return description


if __name__ == "__main__":
    app_type = ask_for_app_type();
    user_id = str(uuid.uuid4());
    app_id = save_app(user_id, app_type)
    description = ask_for_main_app_definition();
    save_progress(app_id, 'main_description', description);
    user_flows = break_down_user_flows(description);

