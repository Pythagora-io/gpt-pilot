import pytest
from pilot.utils.style import color_text
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Test data: tuples of (text, color_name, bold, enable_formatting, expected_output)
TEST_DATA = [
    ("Hello, World!", "red", True, True, f"{Fore.RED}{Style.BRIGHT}Hello, World!"),
    ("Hello, World!", "blue", False, True, f"{Fore.BLUE}Hello, World!"),
    ("Hello, World!", "green", True, False, "Hello, World!"),
    ("Hello, World!", "invalid_color", True, True, f"{Fore.WHITE}{Style.BRIGHT}Hello, World!"),
]


@pytest.mark.parametrize("text,color_name,bold,enable_formatting,expected_output", TEST_DATA)
def test_color_text(text, color_name, bold, enable_formatting, expected_output):
    result = color_text(text, color_name, bold, enable_formatting)

    # Print the colored text to the console
    print(result)

    # Assert that the function output is as expected
    assert result == expected_output

