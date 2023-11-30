from colorama import Fore, Style as ColoramaStyle, init
from enum import Enum
from questionary import Style

# Initialize colorama. Ensures that ANSI codes work on Windows systems.
init(autoreset=True)


class Theme(Enum):
    """
    Enum representing themes, which can be either DARK or LIGHT.
    """
    DARK = 'dark'
    LIGHT = 'light'
    YELLOW = 'yellow'


class ColorName(Enum):
    """
    Enum representing color names and their corresponding ANSI color codes.
    Each color has a normal and a light version, indicated by the two elements in the tuple.
    """
    RED = (Fore.RED, Fore.LIGHTRED_EX)
    GREEN = (Fore.GREEN, Fore.LIGHTGREEN_EX)
    YELLOW = (Fore.YELLOW, Fore.LIGHTYELLOW_EX)
    BLUE = (Fore.BLUE, Fore.LIGHTBLUE_EX)
    CYAN = (Fore.CYAN, Fore.LIGHTCYAN_EX)
    WHITE = (Fore.WHITE, Fore.LIGHTWHITE_EX)


THEME_STYLES = {
    # Style configurations for DARK theme
    Theme.DARK: Style.from_dict({
        'question': '#FFFFFF bold',  # the color and style of the question - White
        'answer': '#FF910A bold',  # the color and style of the answer - Dark Orange / Pumpkin
        'pointer': '#FF4500 bold',  # the color and style of the pointer - Orange Red
        'highlighted': '#63CD91 bold',  # the color and style of the highlighted option - Medium Aquamarine
        'instruction': '#FFFF00 bold'  # the color and style of the instruction - Yellow
    }),
    # Style configurations for LIGHT theme
    Theme.LIGHT: Style.from_dict({
        'question': '#000000 bold',  # the color and style of the question - Black
        'answer': '#FFB74D bold',  # the color and style of the answer - Light Orange
        'pointer': '#FF7043 bold',  # the color and style of the pointer - Light Red
        'highlighted': '#AED581 bold',  # the color and style of the highlighted option - Light Green
        'instruction': '#757575 bold'  # the color and style of the instruction - Grey
    }),
    # Style configurations for LIGHT theme
    Theme.YELLOW: Style.from_dict({
        'question': '#FFFF00 bold',  # the color and style of the question - Black
        'answer': '#FFB74D bold',  # the color and style of the answer - Light Orange
        'pointer': '#FF7043 bold',  # the color and style of the pointer - Light Red
    })
}


class ThemeStyle:
    """
    Class that provides style configurations for DARK and LIGHT themes.
    """

    def __init__(self, theme):
        """
        Initializes a ThemeStyle instance.

        Args:
            theme (Theme): An enum member indicating the theme to use.
        """
        self.theme = theme

    def get_style(self):
        """
        Returns the Style configuration for the current theme.

        Returns:
            questionary.Style: The Style instance for the current theme.
        """
        return THEME_STYLES[self.theme]


class StyleConfig:
    """
    Class to manage the application's style and color configurations.
    """

    def __init__(self, theme: Theme = Theme.DARK):
        """
        Initializes a StyleConfig instance.

        Args:
            theme (Theme, optional): The initial theme to use. Defaults to Theme.DARK.
        """
        self.theme_style = ThemeStyle(theme)
        self.theme = theme

    def get_style(self):
        """
        Retrieves the Style configuration from the theme_style instance.

        Returns:
            questionary.Style: The Style configuration.
        """
        return self.theme_style.get_style()

    def get_color(self, color_name: ColorName):
        """
        Retrieves the ANSI color code for the provided color_name, taking into account the current theme.

        Args:
            color_name (ColorName): Enum member indicating the desired color.

        Returns:
            str: The ANSI color code.
        """
        return color_name.value[self.theme == Theme.LIGHT]

    def set_theme(self, theme: Theme):
        """
        Updates the theme of both the StyleConfig and its theme_style instance.

        Args:
            theme (Theme): Enum member indicating the new theme.
        """
        self.theme = theme
        self.theme_style.theme = theme


def get_color_function(color_name: ColorName, bold: bool = False):
    """
    Returns a function that colorizes text using the provided color_name and optionally makes it bold.

    Args:
        color_name (ColorName): Enum member indicating the color to use.
        bold (bool, optional): If True, the returned function will bold text. Defaults to False.

    Returns:
        Callable[[str], str]: A function that takes a string and returns it colorized.
    """

    def color_func(text: str) -> str:
        """
        Colorizes the input text using the color and boldness provided when `get_color_function` was called.

        Args:
            text (str): The text to colorize.

        Returns:
            str: The colorized text.
        """
        color = style_config.get_color(color_name)
        style = ColoramaStyle.BRIGHT if bold else ""
        reset = ColoramaStyle.RESET_ALL  # Reset code to reset the color
        return f'{color}{style}{text}{reset}'

    return color_func


style_config = StyleConfig()

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
