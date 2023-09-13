from unittest.mock import patch
from dotenv import load_dotenv
from .Receptionist import Receptionist
from helpers.Project import Project
from utils.test_utils import mock_terminal_size

load_dotenv()
SEND_TO_LLM = False


@patch('os.get_terminal_size', mock_terminal_size)
class TestReceptionist:
    def setup_method(self):
        name = 'TestReceptionist'
        self.project = Project({
                'app_id': 'test-receptionist',
                'name': name,
                'app_type': ''
            },
            name=name,
            architecture=[],
            user_stories=[],
            current_step='',
        )

        self.receptionist = Receptionist(self.project)

    @patch('helpers.AgentConvo.get_development_step_from_hash_id', return_value=None)
    def test_route_ProductOwner(self, mock_get_dev):
        # Given
        mock_value = {'function_calls': {'arguments': {'agent': 'ProductOwner'}, 'name': 'route_initial_input'}}

        # When
        route = self.call_route_initial_input('A simple chat app with real time communication', mock_value)

        # Then
        assert route == 'ProductOwner'

    @patch('helpers.AgentConvo.get_development_step_from_hash_id', return_value=None)
    def test_route_CodeMonkey(self, mock_get_dev):
        # Given
        mock_value = {'function_calls': {'arguments': {'agent': 'CodeMonkey'}, 'name': 'route_initial_input'}}

        # When
        route = self.call_route_initial_input('Write the word "Washington" to a .txt file', mock_value)

        # Then
        assert route == 'CodeMonkey'

    def call_route_initial_input(self, input_str, mock_return_value=None):
        if SEND_TO_LLM or mock_return_value is None:
            return self.receptionist.route_initial_input(input_str)
        else:
            with patch('utils.llm_connection.stream_gpt_completion', return_value=mock_return_value):
                return self.receptionist.route_initial_input(input_str)
