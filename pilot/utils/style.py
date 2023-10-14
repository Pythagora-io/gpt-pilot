from enum import Enum
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


class Config:
    no_color: bool = False


def disable_color_output():
    Config.no_color = True


class ColorName(Enum):
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE


def color_text(text: str, color_name: ColorName, bold: bool = False) -> str:
    """
    Returns text with a specified color and optional style.

    Args:
        text (str): The text to colorize.
        color_name (ColorName): The color of the text. Should be a member of the ColorName enum.
        bold (bool, optional): If True, the text will be displayed in bold. Defaults to False.

    Returns:
        str: The text with applied color and optional style.
    """
    if Config.no_color:
        return text

    color = color_name.value
    style = Style.BRIGHT if bold else ""
    return f'{color}{style}{text}'


def get_color_function(color_name: ColorName, bold: bool = False):
    """
    Generate and return a function that colorizes input text with the specified color and style.

    Parameters:
        color_name (ColorName): Enum member specifying the text color.
        bold (bool, optional): If True, generated function will produce bold text. Defaults to False.

    Returns:
        Callable[[str], str]: A function that takes a string input and returns it colorized.
    """
    def color_func(text: str) -> str:
        if Config.no_color:
            return text
        return color_text(text, color_name, bold)
    return color_func


# Dynamically generate color functions
color_red = get_color_function(ColorName.RED)
color_red_bold = get_color_function(ColorName.RED, True)
color_green = get_color_function(ColorName.GREEN)
color_green_bold = get_color_function(ColorName.GREEN, True)
color_yellow = get_color_function(ColorName.YELLOW)
color_yellow_bold = get_color_function(ColorName.YELLOW, True)
color_blue = get_color_function(ColorName.BLUE)
color_blue_bold = get_color_function(ColorName.BLUE, True)
color_cyan = get_color_function(ColorName.CYAN)
color_cyan_bold = get_color_function(ColorName.CYAN, True)
color_white = get_color_function(ColorName.WHITE)
color_white_bold = get_color_function(ColorName.WHITE, True)
