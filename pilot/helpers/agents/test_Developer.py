import builtins
import json
import os
import pytest
from unittest.mock import patch, MagicMock

import requests

from helpers.AgentConvo import AgentConvo
from dotenv import load_dotenv
load_dotenv()

from main import get_custom_print
from .Developer import Developer, ENVIRONMENT_SETUP_STEP
from test.mock_questionary import MockQuestionary
from helpers.test_Project import create_project


class TestDeveloper:
    def setup_method(self):
        builtins.print, ipc_client_instance = get_custom_print({})

        name = 'TestDeveloper'
        self.project = create_project()
        self.project.app_id = 'test-developer'
        self.project.name = name
        self.project.set_root_path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              '../../../workspace/TestDeveloper')))

        self.project.technologies = []
        self.project.current_step = ENVIRONMENT_SETUP_STEP
        self.developer = Developer(self.project)

    @pytest.mark.uses_tokens
    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"command": "python --version", "timeout": 10}'})
    @patch('helpers.cli.execute_command', return_value=('', 'DONE', None))
    def test_install_technology(self, mock_execute_command,
                                mock_completion, mock_save, mock_get_saved_step):
        # Given
        self.developer.convo_os_specific_tech = AgentConvo(self.developer)

        # When
        llm_response = self.developer.install_technology('python')

        # Then
        assert llm_response == 'DONE'
        mock_execute_command.assert_called_once_with(self.project, 'python --version', timeout=10, command_id=None)

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"tasks": [{"command": "ls -al"}]}'})
    def test_implement_task(self, mock_completion, mock_save, mock_get_saved_step):
        # Given any project
        project = create_project()
        project.project_description = 'Test Project'
        project.development_plan = [{
            'description': 'Do stuff',
            'user_review_goal': 'Do stuff',
        }]
        project.get_all_coded_files = lambda: []
        project.current_step = 'test'

        # and a developer who will execute any task
        developer = Developer(project)
        developer.execute_task = MagicMock()
        developer.execute_task.return_value = {'success': True}

        # When
        developer.implement_task(0, {'description': 'Do stuff'})

        # Then we parse the response correctly and send list of steps to execute_task()
        assert developer.execute_task.call_count == 1
        assert developer.execute_task.call_args[0][1] == [{'command': 'ls -al'}]

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"tasks": [{"command": "ls -al"}, {"command": "ls -al src"}, {"command": "ls -al test"}, {"command": "ls -al build"}]}'})
    def test_implement_task_reject_with_user_input(self, mock_completion, mock_save, mock_get_saved_step):
        # Given any project
        project = create_project()
        project.project_description = 'Test Project'
        project.development_plan = [{
            'description': 'Do stuff',
            'user_review_goal': 'Do stuff',
        }]
        project.get_all_coded_files = lambda: []
        project.current_step = 'test'

        # and a developer who will execute any task except for `ls -al test`
        developer = Developer(project)
        developer.execute_task = MagicMock()
        developer.execute_task.side_effect = [
            {'success': False, 'step_index': 2, 'user_input': 'no, use a better command'},
            {'success': True}
        ]

        # When
        developer.implement_task(0, {'description': 'Do stuff'})

        # Then we include the user input in the conversation to update the task list
        assert mock_completion.call_count == 3
        prompt = mock_completion.call_args_list[2].args[0][2]['content']
        assert prompt.startswith('''
# Completed Task Steps:
```
[{'command': 'ls -al'}, {'command': 'ls -al src'}]
```

# Current Step:
This step will not be executed. no, use a better command
```
{'command': 'ls -al test'}
```

# Next Task Steps:
```
[{'command': 'ls -al build'}]
```'''.lstrip())
        assert 'no, use a better command' in prompt
        # and call `execute_task()` again
        assert developer.execute_task.call_count == 2

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    # GET_TEST_TYPE has optional properties, so we need to be able to handle missing args.
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"type": "command_test", "command": {"command": "npm run test", "timeout": 3000}}'})
    # 2nd arg of return_value: `None` to debug, 'DONE' if successful
    @patch('helpers.cli.execute_command', return_value=('stdout:\n```\n\n```', 'DONE', None))
    # @patch('helpers.cli.ask_user', return_value='yes')
    # @patch('helpers.cli.get_saved_command_run')
    def test_code_changes_command_test(self, mock_get_saved_step, mock_save, mock_chat_completion,
                               # Note: the 2nd line below will use the LLM to debug, uncomment the @patches accordingly
                               mock_execute_command):
                               # mock_ask_user, mock_get_saved_command_run):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name

        # When
        # "Now, we need to verify if this change was successfully implemented...
        result = self.developer.test_code_changes(monkey, convo)

        # Then
        assert result == {'success': True, 'cli_response': 'stdout:\n```\n\n```'}

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    # GET_TEST_TYPE has optional properties, so we need to be able to handle missing args.
    @patch('helpers.AgentConvo.create_gpt_chat_completion',
           return_value={'text': '{"type": "manual_test", "manual_test_description": "Does it look good?"}'})
    @patch('helpers.Project.ask_user', return_value='continue')
    def test_code_changes_manual_test_continue(self, mock_get_saved_step, mock_save, mock_chat_completion, mock_ask_user):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name

        # When
        result = self.developer.test_code_changes(monkey, convo)

        # Then
        assert result == {'success': True, 'user_input': 'continue'}

    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('helpers.AgentConvo.create_gpt_chat_completion')
    @patch('utils.questionary.get_saved_user_input')
    # https://github.com/Pythagora-io/gpt-pilot/issues/35
    def test_code_changes_manual_test_no(self, mock_get_saved_user_input, mock_chat_completion, mock_save, mock_get_saved_step):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name
        convo.load_branch = lambda function_uuid=None: function_uuid
        self.project.developer = self.developer

        mock_chat_completion.side_effect = [
            {'text': '{"type": "manual_test", "manual_test_description": "Does it look good?"}'},
            {'text': '{"thoughts": "hmmm...", "reasoning": "testing", "steps": [{"type": "command", "command": {"command": "something scary", "timeout": 3000}, "check_if_fixed": true}]}'},
            {'text': 'do something else scary'},
        ]

        mock_questionary = MockQuestionary(['no', 'no'])

        with patch('utils.questionary.questionary', mock_questionary):
            # When
            result = self.developer.test_code_changes(monkey, convo)

            # Then
            assert result == {'success': True, 'user_input': 'no'}

    @patch('helpers.cli.execute_command', return_value=('stdout:\n```\n\n```', 'DONE', None))
    @patch('helpers.AgentConvo.get_saved_development_step')
    @patch('helpers.AgentConvo.save_development_step')
    @patch('utils.llm_connection.requests.post')
    @patch('utils.questionary.get_saved_user_input')
    def test_test_code_changes_invalid_json(self, mock_get_saved_user_input,
                                            mock_requests_post,
                                            mock_save,
                                            mock_get_saved_step,
                                            mock_execute,
                                            monkeypatch):
        # Given
        monkey = None
        convo = AgentConvo(self.developer)
        convo.save_branch = lambda branch_name=None: branch_name
        convo.load_branch = lambda function_uuid=None: function_uuid
        self.project.developer = self.developer

        # we send a GET_TEST_TYPE spec, but the 1st response is invalid
        types_in_response = ['command', 'wrong_again', 'command_test']
        json_received = []

        def generate_response(*args, **kwargs):
            # Copy messages, including the validation errors from the request
            content = [msg['content'] for msg in kwargs['json']['messages']]
            json_received.append(content)

            gpt_response = json.dumps({
                'type': types_in_response.pop(0),
                'command': {
                    'command': 'node server.js',
                    'timeout': 3000
                }
            })
            choice = json.dumps({'delta': {'content': gpt_response}})
            line = json.dumps({'choices': [json.loads(choice)]}).encode('utf-8')

            response = requests.Response()
            response.status_code = 200
            response.iter_lines = lambda: [line]
            print(f'##### mock response: {response}')
            return response

        mock_requests_post.side_effect = generate_response
        monkeypatch.setenv('OPENAI_API_KEY', 'secret')

        # mock_questionary = MockQuestionary([''])

        # with patch('utils.questionary.questionary', mock_questionary):
        # When
        result = self.developer.test_code_changes(monkey, convo)

        # Then
        assert result == {'success': True, 'cli_response': 'stdout:\n```\n\n```'}
        assert mock_requests_post.call_count == 3
        assert "The JSON is invalid at $.type - 'command' is not one of " \
               "['automated_test', 'command_test', 'manual_test', 'no_test']" in json_received[1][3]
        assert mock_execute.call_count == 1
