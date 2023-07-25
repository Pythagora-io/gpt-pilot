# utils/utils.py
import inquirer
from inquirer.themes import GreenPassion


def break_down_user_flows(description):
    return 'false'
    user_flows = parse_description_into_user_flows(description)
    for flow_index, user_flow in enumerate(user_flows):
        is_correct = False
        while not is_correct:
            print(f"User Flow {flow_index + 1}: {user_flow}")
            is_correct = ask_for_user_flow_confirmation(flow_index)
        save_progress(app_id, f'user_flow_{flow_index + 1}', user_flow)


def ask_for_user_flow_confirmation(flow_index):
    questions = [
        inquirer.List('confirmation',
                      message=f"Does user flow {flow_index + 1} meet your requirements? (Yes/No)",
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
        inquirer.Text('correction', message=f"Please provide corrections for user flow {flow_index + 1}.")
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())
    if answers is None:
        print("No input provided!")
        return False

    user_flows[flow_index] = answers['correction']
    return False
