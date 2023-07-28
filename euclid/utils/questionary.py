from prompt_toolkit.styles import Style
import questionary

custom_style = Style.from_dict({
    'question': '#FFFFFF bold',  # the color and style of the question
    'answer': '#FF910A bold',  # the color and style of the answer
    'pointer': '#FF4500 bold',  # the color and style of the selection pointer
    'highlighted': '#63CD91 bold',  # the color and style of the highlighted choice
    'instruction': '#FFFF00 bold'  # the color and style of the question mark
})


def styled_select(*args, **kwargs):
    kwargs["style"] = custom_style  # Set style here
    return questionary.select(*args, **kwargs).ask()  # .ask() is included here


def styled_text(*args, **kwargs):
    kwargs["style"] = custom_style  # Set style here
    return questionary.text(*args, **kwargs).ask()  # .ask() is included here
