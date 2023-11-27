import unittest
from pilot.utils.style import style_config, Theme, ColorName, get_color_function


class TestColorStyle(unittest.TestCase):
    def test_initialization(self):
        print("\n[INFO] Testing Theme Initialization...")
        style_config.set_theme(Theme.DARK)
        print(f"[INFO] Set theme to: {Theme.DARK}, Current theme: {style_config.theme}")
        self.assertEqual(style_config.theme, Theme.DARK)

        style_config.set_theme(Theme.LIGHT)
        print(f"[INFO] Set theme to: {Theme.LIGHT}, Current theme: {style_config.theme}")
        self.assertEqual(style_config.theme, Theme.LIGHT)

    def test_color_function(self):
        dark_color_codes = {
            ColorName.RED: "\x1b[31m",
            ColorName.GREEN: "\x1b[32m",
            # ... other colors
        }
        light_color_codes = {
            ColorName.RED: "\x1b[91m",
            ColorName.GREEN: "\x1b[92m",
            # ... other colors
        }
        reset = "\x1b[0m"

        # Test DARK theme
        print("\n[INFO] Testing DARK Theme Colors...")
        style_config.set_theme(Theme.DARK)
        for color_name, code in dark_color_codes.items():
            with self.subTest(color=color_name):
                color_func = get_color_function(color_name, bold=False)
                print(f"[INFO] Testing color: {color_name}, Expect: {code}Test, Got: {color_func('Test')}")
                self.assertEqual(color_func("Test"), f"{code}Test{reset}")

                color_func = get_color_function(color_name, bold=True)
                print(
                    f"[INFO] Testing color (bold): {color_name}, Expect: {code}\x1b[1mTest, Got: {color_func('Test')}")
                self.assertEqual(color_func("Test"), f"{code}\x1b[1mTest{reset}")

        # Test LIGHT theme
        print("\n[INFO] Testing LIGHT Theme Colors...")
        style_config.set_theme(Theme.LIGHT)
        for color_name, code in light_color_codes.items():
            with self.subTest(color=color_name):
                color_func = get_color_function(color_name, bold=False)
                print(f"[INFO] Testing color: {color_name}, Expect: {code}Test, Got: {color_func('Test')}")
                self.assertEqual(color_func("Test"), f"{code}Test{reset}")

                color_func = get_color_function(color_name, bold=True)
                print(
                    f"[INFO] Testing color (bold): {color_name}, Expect: {code}\x1b[1mTest, Got: {color_func('Test')}")
                self.assertEqual(color_func("Test"), f"{code}\x1b[1mTest{reset}")
