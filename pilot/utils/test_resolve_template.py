import unittest
from unittest.mock import patch, MagicMock
from utils.utils import resolveTemplate

class TestResolveTemplate(unittest.TestCase):

    def setUp(self):
        # Patch 'os.path.exists' to simulate file existence checks
        self.mock_exists = patch('utils.utils.os.path.exists').start()
        # Patch 'get_template' for both override and primary environments
        self.mock_primary_get_template = patch('utils.utils.primary_env.get_template').start()
        self.mock_override_get_template = patch('utils.utils.override_env.get_template').start()
        self.addCleanup(patch.stopall)  # Ensure all patches are stopped after each test

        # Setup a mock template that will be returned by get_template calls
        self.mock_template = MagicMock()

    def test_model_specific_override(self):
        self.mock_exists.side_effect = lambda path: 'model_specific' in path
        self.mock_override_get_template.return_value = self.mock_template

        resolveTemplate('prompt_name', 'model_specific')

        self.mock_exists.assert_called()
        self.mock_override_get_template.assert_called_once_with('model_specific/prompt_name')

    def test_general_override(self):
        self.mock_exists.return_value = True
        self.mock_override_get_template.return_value = self.mock_template

        resolveTemplate('prompt_name')

        self.mock_exists.assert_called()
        self.mock_override_get_template.assert_called_once_with('prompt_name')

    def test_primary_environment(self):
        self.mock_exists.return_value = False
        self.mock_primary_get_template.return_value = self.mock_template

        resolveTemplate('prompt_name')

        self.mock_exists.assert_called()
        self.mock_primary_get_template.assert_called_once_with('prompt_name')

    def test_invalid_model_or_prompt(self):
        self.mock_exists.return_value = False
        self.mock_primary_get_template.side_effect = Exception("Template not found")

        with self.assertRaises(Exception) as context:
            resolveTemplate('invalid_prompt', 'invalid_model')
        self.assertIn("Template not found", str(context.exception))

    def test_both_model_specific_and_general_override_present(self):
        self.mock_exists.side_effect = [True, True]  # Both model-specific and general files exist
        self.mock_override_get_template.return_value = self.mock_template

        resolveTemplate('prompt_name', 'model_specific')
        self.mock_override_get_template.assert_called_once_with('model_specific/prompt_name')

    def test_no_template_found_anywhere(self):
        self.mock_exists.return_value = False
        self.mock_primary_get_template.side_effect = Exception("Template not found")
        self.mock_override_get_template.side_effect = Exception("Template not found")

        with self.assertRaises(Exception) as context:
            resolveTemplate('nonexistent_prompt')
        self.assertIn("Template not found", str(context.exception))

if __name__ == '__main__':
    unittest.main()
