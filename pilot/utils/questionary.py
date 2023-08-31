from prompt_toolkit.styles import Style
import questionary
from termcolor import colored

from database.database import save_user_input, get_user_input_from_hash_id
from const.ipc import MESSAGE_TYPE

custom_style = Style.from_dict({
    'question': '#FFFFFF bold',  # the color and style of the question
    'answer': '#FF910A bold',  # the color and style of the answer
    'pointer': '#FF4500 bold',  # the color and style of the selection pointer
    'highlighted': '#63CD91 bold',  # the color and style of the highlighted choice
    'instruction': '#FFFF00 bold'  # the color and style of the question mark
})


def styled_select(*args, **kwargs):
    kwargs["style"] = custom_style  # Set style here
    return questionary.select(*args, **kwargs).unsafe_ask()  # .ask() is included here


def styled_text(project, question):
    project.user_inputs_count += 1
    user_input = get_user_input_from_hash_id(project, question)
    if user_input is not None and user_input.user_input is not None and project.skip_steps:
        # if we do, use it
        project.checkpoints['last_user_input'] = user_input
        print(colored(f'Restoring user input id {user_input.id}: ', 'yellow'), end='')
        print(colored(f'{user_input.user_input}', 'yellow', attrs=['bold']))
        return user_input.user_input

    if project.ipc_client_instance is None or project.ipc_client_instance.client is None:
        config = {
            'style': custom_style,
        }
        response = questionary.text(question, **config).unsafe_ask()  # .ask() is included here
    else:
        response = project.log(question, MESSAGE_TYPE['user_input_request'])
        project.log(response, MESSAGE_TYPE['verbose'])

    user_input = save_user_input(project, question, response)

    print('\n\n', end='')

    return response
