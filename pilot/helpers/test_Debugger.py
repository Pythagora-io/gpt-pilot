import builtins
import pytest
from unittest.mock import patch
from dotenv import load_dotenv

load_dotenv()
from pilot.utils.custom_print import get_custom_print
from pilot.helpers.agents.Developer import Developer
from pilot.helpers.AgentConvo import AgentConvo
from pilot.helpers.Debugger import Debugger
from pilot.helpers.test_Project import create_project
from pilot.test.mock_questionary import MockQuestionary


################## NOTE: this test needs to be ran in debug with breakpoints ##################

@pytest.mark.uses_tokens
@patch('pilot.helpers.AgentConvo.get_saved_development_step')
@patch('pilot.helpers.AgentConvo.save_development_step')
@patch('utils.questionary.get_saved_user_input')
@patch('utils.questionary.save_user_input')
@patch('helpers.cli.get_saved_command_run')
@patch('helpers.cli.run_command')
@patch('helpers.cli.save_command_run')
# @patch('pilot.helpers.cli.execute_command', return_value=('', 'DONE', 0))
def test_debug(
        # mock_execute_command,
        mock_save_command, mock_run_command, mock_get_saved_command,
               mock_save_input, mock_user_input, mock_save_step, mock_get_saved_step):
    # Given
    builtins.print, ipc_client_instance = get_custom_print({})
    project = create_project()
    project.current_step = 'coding'
    developer = Developer(project)
    project.developer = developer
    convo = AgentConvo(developer)
    convo.load_branch = lambda x: None

    debugger = Debugger(developer)
    # TODO: mock agent.project.developer.execute_task

    # convo.messages.append()
    convo.construct_and_add_message_from_prompt('dev_ops/ran_command.prompt', {
        'cli_response': '''
stderr:
```
node:internal/modules/cjs/loader:1080
  throw err;
  ^

Error: Cannot find module 'mime'
Require stack:
- /workspace/chat_app/node_modules/send/index.js
- /workspace/chat_app/node_modules/express/lib/utils.js
- /workspace/chat_app/node_modules/express/lib/application.js
- /workspace/chat_app/node_modules/express/lib/express.js
- /workspace/chat_app/node_modules/express/index.js
- /workspace/chat_app/server.js
    at Module._resolveFilename (node:internal/modules/cjs/loader:1077:15)
    at Module._load (node:internal/modules/cjs/loader:922:27)
    at Module.require (node:internal/modules/cjs/loader:1143:19)
    at require (node:internal/modules/cjs/helpers:121:18)
    at Object.<anonymous> (/workspace/chat_app/node_modules/send/index.js:24:12)
    at Module._compile (node:internal/modules/cjs/loader:1256:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1310:10)
    at Module.load (node:internal/modules/cjs/loader:1119:32)
    at Module._load (node:internal/modules/cjs/loader:960:12)
```
stdout:
```
> chat_app@1.0.0 start
> node server.js
```        
'''
    })

    mock_questionary = MockQuestionary(['', ''])

    with patch('utils.questionary.questionary', mock_questionary):
        # When
        result = debugger.debug(convo, command={'command': 'npm run start'}, is_root_task=True)

        # Then
        assert result == {'success': True}
