import os
from enum import Enum
from colorama import Fore, Style, init

init(autoreset=True)


class ColorName(Enum):
    BLACK = Fore.BLACK
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE


class Config:
    # Use environment variable or default value for NO_COLOR
    NO_COLOR = os.environ.get("NO_COLOR", False)


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
    # If NO_COLOR is True, return unmodified text
    if Config.NO_COLOR:
        return text

    # Use the color value from the enum
    color = color_name.value
    # Apply BRIGHT style if bold is True, otherwise use an empty string
    style = Style.BRIGHT if bold else ""
    # Return the formatted text
    return f'{color}{style}{text}'


# Example usage:
if __name__ == "__main__":
    print(color_text("This is black text", ColorName.BLACK))
    print(color_text("This is red text", ColorName.RED))
    print(color_text("This is green text", ColorName.GREEN, bold=True))
    print(color_text("This is yellow text", ColorName.YELLOW))
    print(color_text("This is blue text", ColorName.BLUE, bold=True))
    print(color_text("This is cyan text", ColorName.CYAN))
    print(color_text("This is white text", ColorName.WHITE, bold=True))
