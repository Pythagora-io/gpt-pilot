import builtins
from unittest.mock import MagicMock
from dotenv import load_dotenv
from helpers.agents.Developer import Developer
from helpers.AgentConvo import AgentConvo
from utils.custom_print import get_custom_print

load_dotenv()

builtins.print, ipc_client_instance = get_custom_print({})


def test_agent_convo_model_resolve():
    # Given
    project = MagicMock()
    developer = Developer(project)
    convo = AgentConvo(developer)

    # Then
    assert convo.model == 'gpt-4-turbo-preview'

def test_agent_convo_model_resolve_model_as_constructor_arg():
    # Given
    model = "SOME_MODEL"
    project = MagicMock()
    developer = Developer(project)
    convo = AgentConvo(developer, model=model)

    # Then
    assert convo.model == model

# def test_format_message_content_json_response():
#     # Given
#     project = create_project()
#     project.current_step = 'test'
#     developer = Developer(project)
#     convo = AgentConvo(developer)
#
#     response = {
#         'files': [
#             {
#                 'name': 'package.json',
#                 'path': '/package.json',
#                 'content': '{\n  "name": "complex_app",\n  "version": "1.0.0",\n  "description": "",\n  "main": "index.js",\n  "directories": {\n    "test": "tests"\n  },\n  "scripts": {\n    "test": "echo \\"Error: no test specified\\" && exit 1",\n    "start": "node index.js"\n  },\n  "keywords": [],\n  "author": "",\n  "license": "ISC",\n  "dependencies": {\n    "axios": "^1.5.1",\n    "express": "^4.18.2",\n    "mongoose": "^7.6.1",\n    "socket.io": "^4.7.2"\n  },\n  "devDependencies": {\n    "nodemon": "^3.0.1"\n  }\n}'
#             }
#         ]
#     }
#
#     # When
#     message_content = convo.format_message_content(response, IMPLEMENT_TASK)
#
#     # Then
#     assert message_content == '''
# # files
# ##0
# name: package.json
# path: /package.json
# content: {
#   "name": "complex_app",
#   "version": "1.0.0",
#   "description": "",
#   "main": "index.js",
#   "directories": {
#     "test": "tests"
#   },
#   "scripts": {
#     "test": "echo \\"Error: no test specified\\" && exit 1",
#     "start": "node index.js"
#   },
#   "keywords": [],
#   "author": "",
#   "license": "ISC",
#   "dependencies": {
#     "axios": "^1.5.1",
#     "express": "^4.18.2",
#     "mongoose": "^7.6.1",
#     "socket.io": "^4.7.2"
#   },
#   "devDependencies": {
#     "nodemon": "^3.0.1"
#   }
# }'''.lstrip()
