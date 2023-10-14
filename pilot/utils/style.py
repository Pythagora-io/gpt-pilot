from colorama import Fore, Style, init

init()

def red(text):
    return f'{Fore.RED}{text}{Style.RESET_ALL}'


def red_bold(text):
    return f'{Fore.RED}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def yellow(text):
    return f'{Fore.YELLOW}{text}{Style.RESET_ALL}'


def yellow_bold(text):
    return f'{Fore.YELLOW}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def green(text):
    return f'{Fore.GREEN}{text}{Style.RESET_ALL}'


def green_bold(text):
    return f'{Fore.GREEN}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def blue(text):
    return f'{Fore.BLUE}{text}{Style.RESET_ALL}'


def blue_bold(text):
    return f'{Fore.BLUE}{Style.BRIGHT}{text}{Style.RESET_ALL}'


def cyan(text):
    return f'{Fore.CYAN}{text}{Style.RESET_ALL}'


def white(text):
    return f'{Fore.WHITE}{text}{Style.RESET_ALL}'


def white_bold(text):
    return f'{Fore.WHITE}{Style.BRIGHT}{text}{Style.RESET_ALL}'


from colorama import Fore, Style, init

init(autoreset=True)

COLORS = {
    "red": Fore.RED,
    "green": Fore.GREEN,
    "yellow": Fore.YELLOW,
    "blue": Fore.BLUE,
    "cyan": Fore.CYAN,
    "white": Fore.WHITE,
}


def color_text(text: str, color_name: str, bold: bool = False, enable_formatting: bool = True) -> str:
    """
    Returns text with a specified color and optional style.

    Args:
        text (str): The text to colorize.
        color_name (str): The color of the text. Should be a key in the COLORS dictionary.
        bold (bool, optional): If True, the text will be displayed in bold. Defaults to False.
        enable_formatting (bool, optional): If True, ANSI codes will be applied. Defaults to True.

    Returns:
        str: The text with applied color and optional style.

    Example:
        >>> color_text("Hello, World!", "red", True, enable_formatting=False)
        'Hello, World!'
    """
    if not enable_formatting:
        return text

    color = COLORS.get(color_name, Fore.WHITE)  # Default color is white
    style = Style.BRIGHT if bold else ""
    return f'{color}{style}{text}'

