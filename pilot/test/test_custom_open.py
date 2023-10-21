import unittest
import os
import builtins
from utils.custom_open import get_custom_open, built_in_open

builtins.open = get_custom_open


class TestCustomOpenFunction(unittest.TestCase):

    def setUp(self):
        self.test_filename = "test_file.txt"
        self.test_content = "This is a test content."

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_utf8_encoding_by_default(self):
        with open(self.test_filename, 'w') as f:
            f.write(self.test_content)

        with built_in_open(self.test_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, self.test_content)

    def test_explicit_encoding_overrides_default(self):
        # Write using latin-1 encoding
        with open(self.test_filename, 'w', encoding='latin-1') as f:
            f.write('©')

        # Check with latin-1 encoding
        with built_in_open(self.test_filename, 'r', encoding='latin-1') as f:
            content = f.read()
            self.assertEqual(content, '©')

    def test_binary_mode_no_encoding(self):
        with open(self.test_filename, 'wb') as f:
            f.write(b'\x80abc')

        with built_in_open(self.test_filename, 'rb') as f:
            content = f.read()
            self.assertEqual(content, b'\x80abc')

    def test_read_write_binary_mode(self):
        # Test combinations like 'r+b'
        with open(self.test_filename, 'w') as f:
            f.write(self.test_content)

        with open(self.test_filename, 'r+b') as f:
            content = f.read().decode('utf-8')
            self.assertEqual(content, self.test_content)
            f.write(b' additional content')

        with open(self.test_filename, 'r') as f:
            content = f.read()
            expected_content = self.test_content + " additional content"
            self.assertEqual(content, expected_content)
