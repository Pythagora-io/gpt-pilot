import unittest
from unittest.mock import patch, MagicMock
from jinja2 import TemplateNotFound
from utils.utils import resolve_template

class TestResolveTemplate(unittest.TestCase):

    def setUp(self):
        # Patch 'Environment.get_template' to simulate template retrieval
        self.mock_get_template = patch('utils.utils.env.get_template').start()
        self.addCleanup(patch.stopall)  # Ensure all patches are stopped after each test

        # Setup a mock template that will be returned by get_template calls
        self.mock_template = MagicMock(name='MockTemplate')
        self.mock_get_template.return_value = self.mock_template

    def test_model_specific_template(self):
        """Test that a model-specific template is correctly resolved."""
        template_name = resolve_template('prompt_name', 'model_specific')
        self.mock_get_template.assert_called_once_with('model_specific/prompt_name')
        self.assertEqual(template_name, self.mock_template)

    def test_fallback_to_general_template_when_model_specific_not_found(self):
        """Test fallback to general template when model-specific is not found."""
        # Correctly instantiate TemplateNotFound with the 'name' argument for the model-specific template
        self.mock_get_template.side_effect = [TemplateNotFound(name='model_specific/prompt_name'), self.mock_template]

        template = resolve_template('prompt_name', 'model_specific')

        # Assertions remain the same
        self.assertEqual(template, self.mock_template)
        self.mock_get_template.assert_has_calls([
            unittest.mock.call('model_specific/prompt_name'),  # Attempted and failed
            unittest.mock.call('prompt_name')  # Fallback attempt
        ], any_order=False)  # Ensures the call order matches

    def test_general_template_without_model(self):
        """Test resolving a general template without specifying a model."""
        template_name = resolve_template('prompt_name')
        self.mock_get_template.assert_called_once_with('prompt_name')
        self.assertEqual(template_name, self.mock_template)

    def test_template_not_found_raises_exception(self):
        """Test that an appropriate exception is raised when no template is found."""
        self.mock_get_template.side_effect = FileNotFoundError

        with self.assertRaises(FileNotFoundError):
            resolve_template('nonexistent_prompt')

    def test_model_specific_template_resolution(self):
        """Test resolution of a model-specific template."""
        # Assuming 'model_specific/prompt_name' exists
        self.mock_get_template.return_value = self.mock_template
        template = resolve_template('prompt_name', 'model_specific')
        
        # Verify the correct template was retrieved
        self.mock_get_template.assert_called_once_with('model_specific/prompt_name')
        self.assertEqual(template, self.mock_template, "The resolved template should match the model-specific template.")


if __name__ == '__main__':
    unittest.main()
