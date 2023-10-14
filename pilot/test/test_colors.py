import pytest
from pilot.utils.style import Config, ColorName, color_text

# Parameters for parametrized tests
colors = [ColorName.RED, ColorName.GREEN, ColorName.YELLOW, ColorName.BLUE, ColorName.CYAN, ColorName.WHITE]
bold_options = [True, False]
no_color_options = [True, False]


@pytest.fixture(params=no_color_options, ids=['no_color', 'color'])
def manage_no_color(request):
    original_no_color = Config.no_color
    Config.no_color = request.param
    yield  # This is where the test function will run.
    Config.no_color = original_no_color  # Restore original state after the test.


@pytest.mark.parametrize("color", colors, ids=[c.name for c in colors])
@pytest.mark.parametrize("bold", bold_options, ids=['bold', 'not_bold'])
def test_color_text(manage_no_color, color, bold):
    """
    Test the function color_text by checking the behavior with various color and bold options,
    while considering the global no_color flag.
    """
    colored_text = color_text("test", color, bold)

    print(
        f"Visual Check - expect {'color (' + color.name + ')' if not Config.no_color else 'no color'}: {colored_text}")

    # Check: if no_color is True, there should be no ANSI codes in the string.
    if Config.no_color:
        assert colored_text == "test"
    else:
        # Ensure the ANSI codes for color and (if applicable) bold styling are present in the string.
        assert color.value in colored_text
        if bold:
            # Check for the ANSI code for bold styling.
            assert "\x1b[1m" in colored_text
        # Ensure the string ends with the original text.
        assert colored_text.endswith("test")

