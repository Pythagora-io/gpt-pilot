import unittest
import os
from utils.custom_open import open, built_in_open


class TestCustomOpenFunction(unittest.TestCase):

    def setUp(self):
        # This method will be called before each test, we can use it to setup any resources.
        self.test_filename = "test_file.txt"
        self.test_content = "This is a test content."

    def tearDown(self):
        # This method will be called after each test, we can use it to free up any resources or do some cleanup.
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_utf8_encoding_by_default(self):
        # Create a file using the custom open with default encoding
        with open(self.test_filename, 'w') as f:
            f.write(self.test_content)

        # Open the file using the built-in open function with utf-8 encoding and check the content
        with built_in_open(self.test_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, self.test_content)

    def test_explicit_encoding_overrides_default(self):
        # Write some bytes that are not valid utf-8 to test explicit encoding
        with built_in_open(self.test_filename, 'wb') as f:
            f.write(b'\x80abc')

        # Attempt to read using the custom open with default utf-8 encoding should raise an exception
        with self.assertRaises(UnicodeDecodeError):
            with open(self.test_filename, 'r') as f:
                f.read()

        # Reading with explicit 'latin-1' encoding should work
        with open(self.test_filename, 'r', encoding='latin-1') as f:
            content = f.read()
            self.assertEqual(content, '\x80abc')
