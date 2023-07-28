from prompt_toolkit.styles import Style
import questionary

custom_style = Style.from_dict({
    'question': '#ff9d00 bold',  # the color and style of the question
    'answer': '#7CFC00 bold',  # the color and style of the answer
    'pointer': '#FF4500 bold',  # the color and style of the selection pointer
    'highlighted': '#800080 bold'  # the color and style of the highlighted choice
})


def styled_select(*args, **kwargs):
    kwargs["style"] = custom_style  # Set style here
    return questionary.select(*args, **kwargs).ask()  # .ask() is included here


def styled_text(*args, **kwargs):
    kwargs["style"] = custom_style  # Set style here
    return questionary.text(*args, **kwargs).ask()  # .ask() is included here
