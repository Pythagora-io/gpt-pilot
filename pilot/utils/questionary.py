import platform
import questionary
import re
import sys
from prompt_toolkit.styles import Style
from utils.style import yellow_bold

from database.database import save_user_input, get_saved_user_input

custom_style = Style.from_dict({
    'question': '#FFFFFF bold',  # the color and style of the question
    'answer': '#FF910A bold',  # the color and style of the answer
    'pointer': '#FF4500 bold',  # the color and style of the selection pointer
    'highlighted': '#63CD91 bold',  # the color and style of the highlighted choice
    'instruction': '#FFFF00 bold'  # the color and style of the question mark
})


def remove_ansi_codes(s: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', s)


def styled_select(*args, **kwargs):
    kwargs["style"] = custom_style
    return questionary.select(*args, **kwargs).unsafe_ask()  # .ask() is included here


def styled_text(project, question, ignore_user_input_count=False, style=None):
    if not ignore_user_input_count:
        project.user_inputs_count += 1
        user_input = get_saved_user_input(project, question)
        if user_input is not None and user_input.user_input is not None and project.skip_steps:
            # if we do, use it
            project.checkpoints['last_user_input'] = user_input
            print(yellow_bold(f'Restoring user input id {user_input.id}: '), end='')
            print(yellow_bold(f'{user_input.user_input}'))
            return user_input.user_input

    if project.ipc_client_instance is None or project.ipc_client_instance.client is None:
        config = {
            'style': style if style is not None else custom_style,
        }
        question = remove_ansi_codes(question)  # Colorama and questionary are not compatible and styling doesn't work
        flush_input()
        response = questionary.text(question, **config).unsafe_ask()  # .ask() is included here
    else:
        response = print(question, type='user_input_request')
        print(response)

    if not ignore_user_input_count:
        user_input = save_user_input(project, question, response)

    print('\n\n', end='')
    return response


def get_user_feedback():
    config = {
        'style': custom_style,
    }
    return questionary.text('How did GPT Pilot do? Were you able to create any app that works? '
                            'Please write any feedback you have or just press ENTER to exit: ', **config).unsafe_ask()


def flush_input():
    """Flush the input buffer, discarding all that's in the buffer."""
    try:
        if platform.system() == 'Windows':
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            import termios
            termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    except (ImportError, OSError):
        pass
