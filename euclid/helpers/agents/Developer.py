import json
from termcolor import colored
from utils.utils import step_already_finished
from helpers.agents.CodeMonkey import CodeMonkey
from logger.logger import logger
from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo
from utils.utils import execute_step, array_of_objects_to_string, generate_app_data
from helpers.cli import build_directory_tree, run_command_until_success, execute_command_and_check_cli_response
from const.function_calls import FILTER_OS_TECHNOLOGIES, DEVELOPMENT_PLAN, EXECUTE_COMMANDS, DEV_STEPS, GET_TEST_TYPE
from database.database import save_progress, get_progress_steps
from utils.utils import get_os_info
from helpers.cli import execute_command

class Developer(Agent):
    def __init__(self, project):
        super().__init__('full_stack_developer', project)

    def start_coding(self):
        self.project.current_step = 'coding'

        # DEVELOPMENT
        print(colored(f"Ok, great, now, let's start with the actual development...\n", "green"))
        logger.info(f"Starting to create the actual code...")

        for i, dev_task in enumerate(self.project.development_plan):
            self.implement_task(self.project.development_plan, i)

        # DEVELOPMENT END

        logger.info('The app is DONE!!! Yay...you can use it now.')

    def implement_task(self, sibling_tasks, current_task_index, parent_task=None):


        # TODO REMOVE
        #sibling_tasks = [{'task_description': 'Set up the Node.js project', 'programmatic_goal': 'A valid package.json file is created once `npm init` command is run', 'user_review_goal': 'Project can be initialized using `npm init` command'}, {'task_description': 'Install necessary packages', 'programmatic_goal': 'Package.json file should include socket.io, mongoose, jest, and cypress after running `npm install socket.io mongoose jest cypress bootstrap` command', 'user_review_goal': 'Program dependencies are successfully installed via `npm install`'}, {'task_description': 'Set up an express server', 'programmatic_goal': 'Express server needs to be able to start running on a port 3000 responding all requests with status code 200', 'user_review_goal': 'User needs to be able to run the server by running a command `npm run start` and access the URL `http://localhost:3000` in a browser'}, {'task_description': 'Setup front-end serving static HTML, CSS and JavaScript', 'programmatic_goal': 'On accessing `http://localhost:3000`, express server should serve an index.html file with related styles.css and app.js', 'user_review_goal': 'User should see a basic front-end of the web app on accessing `http://localhost:3000`'}, {'task_description': 'Create chat room functionality', 'programmatic_goal': "On client socket emitting 'create', server socket should emit unique room id back to the client", 'user_review_goal': 'User should be able to create a room and see a unique room id shown on the screen'}, {'task_description': 'Join chat room functionality', 'programmatic_goal': "On client socket emitting 'join' with room id, server socket should emit 'joined' event back to the client", 'user_review_goal': 'User should be able to enter a room id and join the room'}, {'task_description': 'Send and receive messages', 'programmatic_goal': "On client socket emitting 'message', server should broadcast this to all clients in the same room", 'user_review_goal': 'User should be able to type a message, send it, and see it appear in the chat'}, {'task_description': 'Store messages in MongoDB through Mongoose', 'programmatic_goal': "On receiving a 'message' event, server should store the message in MongoDB with proper fields like room id, user, and timestamp", 'user_review_goal': 'User messages are stored and retrieved in chat history when rejoining the room'}, {'task_description': 'Write functional tests with Jest', 'programmatic_goal': 'Functional tests written with Jest validate the message storing and broadcasting process and all tests should pass', 'user_review_goal': 'All functional tests run successfully validating user functionalities'}, {'task_description': 'Write end-to-end tests with Cypress', 'programmatic_goal': 'End-to-end tests validate the chat system as a whole, including sending and receiving messages in a chat room, and all tests should pass', 'user_review_goal': 'All end-to-end tests run successfully validating chat room system as a whole'}]
        # parent_task = {'task_description': 'Set up the Node.js project', 'programmatic_goal': 'A valid package.json file is created once `npm init` command is run', 'user_review_goal': 'Project can be initialized using `npm init` command'}
        # sibling_tasks = [{'type': 'COMMAND', 'description': 'Run `mkdir euclid` to create a new directory for the project'}, {'type': 'COMMAND', 'description': 'Navigate to the newly created directory using `cd euclid`'}, {'type': 'COMMAND', 'description': 'Initialize npm using `npm init -y` to create a new `package.json` file with default values'}, {'type': 'CODE_CHANGE', 'description': 'Verify that the `package.json` file is created in the root directory of the project'}, {'type': 'CODE_CHANGE', 'description': "Write a test in Jest to verify that the `package.json` file is a valid JSON file and contains needed fields such as 'name', 'version', 'main' and 'scripts'"}]
        #current_task_index = 2
        # TODO END
        convo_dev_task = AgentConvo(self)
        task_steps, type = convo_dev_task.send_message('development/task/breakdown.prompt', {
            "app_summary": self.project.high_level_summary,
            "clarification": [],
            "user_stories": self.project.user_stories,
            "user_tasks": self.project.user_tasks,
            "technologies": self.project.architecture,
            "array_of_objects_to_string": array_of_objects_to_string,
            # TODO remove hardcoded folder path
            "directory_tree": self.project.get_directory_tree(),
            "current_task_index": current_task_index,
            "sibling_tasks": sibling_tasks,
            "parent_task": parent_task,
        }, DEV_STEPS)




        self.execute_task(task_steps)







        # TODO REMOVE
        # convo_dev_task.messages = [{'role': 'system', 'content': 'You are a full stack software developer who works in a software development agency. You write very modular code and you practice TDD (test driven development) whenever is suitable to use it. Your job is to implement tasks that your tech lead assigns you. Each task has a description of what needs to be implemented, a programmatic goal that will determine if a task can be marked as done from a programmatic perspective (this is basically a blueprint for an automated test that is run before you send the task for a review to your tech lead) and user-review goal that will determine if a task is done or not but from a user perspective since it will be reviewed by a human.'}, {'role': 'user', 'content': 'You are working on a web app called Euclid and you need to write code for the entire application based on the tasks that the tech lead gives you. So that you understand better what you\'re working on, you\'re given other specs for Euclid as well.\n\nHere is a high level description of Euclid:\n```\nThe client wants to create a simple chat application named "Euclid". This application would not include any authentication and operates solely on localhost. Key features include the ability to create chat rooms and provide users with access to a room via a specific room id. Clarifications have been made regarding the storage, notification mechanism, and chat room design. Messages exchanged in the chat rooms will be stored in a database. However, no notification mechanism is required if a user receives a message while being in another chat room. Lastly, the application is specifically designed for one-on-one chats.\n```\n\nHere are user stories that specify how users use Euclid:\n```\n- As a user, I can create a new chat room using the \'Create\' functionality provided in the Euclid application.\n- As a user, I can share my chat room\'s unique id with another user to allow them to join the chat room.\n- As a user, I can join a chat room by entering a specific room id.\n- As a user, I can send messages to another user within a chat room, and this conversational data will be stored in a database.\n- As a user, I will not receive notifications if I receive a message while being in another chat room.\n- As a user, I can exchange messages in a One-on-One chat format.\n```\n\nHere are user tasks that specify what users need to do to interact with Euclid:\n```\n- User opens the Euclid application on localhost\n- User clicks on the \'Create\' button to create a new chat room\n- User shares the unique chat room id to allow another user to join\n- User enters a specific room id in the \'Join Room\' input to join a pre-existing chat room\n- User writes a message in the chat box and clicks \'Send\' to communicate within a chat room\n- User check and see messages stored in the chat room database\n- User can switch between chat rooms, understanding messages will not be received from other rooms simultaneously\n- User can engage in one-on-one conversation with another user in a chat room\n```\n\nHere are the technologies that you need to use for this project:\n```\n- Node.js\n- Socket.io\n- MongoDB\n- Mongoose\n- Jest\n- Cypress\n- Bootstrap\n- Vanilla Javascript\n- Cronjob\n```\n\n\n\n\nSo far, tasks \n\n    \n\n    \n\n#{\'task_description\': \'Set up the Node.js project\', \'programmatic_goal\': \'A valid package.json file is created once `npm init` command is run\', \'user_review_goal\': \'Project can be initialized using `npm init` command\'}, #{\'task_description\': \'Install necessary packages\', \'programmatic_goal\': \'Package.json file should include socket.io, mongoose, jest, and cypress after running `npm install socket.io mongoose jest cypress bootstrap` command\', \'user_review_goal\': \'Program dependencies are successfully installed via `npm install`\'} are finished so let\'s do\n\n```\ntask_description: Set up an express server\nprogrammatic_goal: Express server needs to be able to start running on a port 3000 responding all requests with status code 200\nuser_review_goal: User needs to be able to run the server by running a command `npm run start` and access the URL `http://localhost:3000` in a browser\n```\n\nThink step by step about what needs to be done to complete this task. \n\n\n\nFirst, just make a list of steps we need to do to fulfill this task. It should be in a JSON array. Every step must NOT contain both a command that needs to be run and the code that needs to be changed. It can be either command (or multiple commands) that need to be run or a change in the code. Each step must start with a keyword `COMMAND` in case the step consists of commands that need to be run or `CODE_CHANGE` in case it consists of changes in the code. After the keyword, write a description of what will be done in that step. Do not write what needs to be done for each step but only list them in an array. Also, keep in mind that you also need to write test (or tests) that will programmatically verify that your task is complete.\n\n'}, {'role': 'assistant', 'content': ('more_tasks', [{'type': 'COMMAND', 'description': 'Install express by running `npm install express`'}, {'type': 'CODE_CHANGE', 'description': 'Create a new file called server.js'}, {'type': 'CODE_CHANGE', 'description': 'In server.js, require express module and initialize a new express application'}, {'type': 'CODE_CHANGE', 'description': 'Set the application to listen on port 3000'}, {'type': 'COMMAND', 'description': 'Test the server by running `node server.js`'}, {'type': 'CODE_CHANGE', 'description': "Add a default route '/' that will respond with status code 200 to all requests"}, {'type': 'CODE_CHANGE', 'description': 'Update package.json to include a `start` script which would run the server.js file'}, {'type': 'CODE_CHANGE', 'description': 'Create a test that will request to URL `http://localhost:3000` and assert that the response status code is 200'}])}]
        # task_steps = [{'type': 'COMMAND', 'description': 'Install express by running `npm install express`'}, {'type': 'CODE_CHANGE', 'description': 'Create a new file called server.js'}, {'type': 'CODE_CHANGE', 'description': 'In server.js, require express module and initialize a new express application'}, {'type': 'CODE_CHANGE', 'description': 'Set the application to listen on port 3000'}, {'type': 'COMMAND', 'description': 'Test the server by running `node server.js`'}, {'type': 'CODE_CHANGE', 'description': "Add a default route '/' that will respond with status code 200 to all requests"}, {'type': 'CODE_CHANGE', 'description': 'Update package.json to include a `start` script which would run the server.js file'}, {'type': 'CODE_CHANGE', 'description': 'Create a test that will request to URL `http://localhost:3000` and assert that the response status code is 200'}]
        # type = 'code_change'
        # TODO REMOVE

        if type == 'run_commands':
            return
            for cmd in task_steps:
                run_command_until_success(cmd['command'], cmd['timeout'], convo_dev_task)
        elif type == 'code_change':
            self.implement_code_changes(task_steps)
        elif type == 'more_tasks':
            if isinstance(task_steps, list):
                for i, step in enumerate(task_steps):
                    self.implement_task(task_steps, i, sibling_tasks[current_task_index])
            else:
                raise Exception('Task steps must be a list.')


    def execute_task(self, task):
        for step in task:
            if step['type'] == 'command':
                continue
                run_command_until_success(cmd['command'], cmd['timeout'], convo_dev_task)
            elif step['type'] == 'code_change':
                self.implement_code_changes(step['description'])
            else:
                raise Exception('Step type must be either run_command or code_change.')
            
    def set_up_environment(self):
        self.project.current_step = 'environment_setup'
        self.convo_os_specific_tech = AgentConvo(self)

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], self.project.current_step)
        if step and not execute_step(self.project.args['step'], self.project.current_step):
            step_already_finished(self.project.args, step)
            return
        
        # ENVIRONMENT SETUP
        print(colored(f"Setting up the environment...\n", "green"))
        logger.info(f"Setting up the environment...")

        # TODO: remove this once the database is set up properly
        # previous_messages[2]['content'] = '\n'.join(previous_messages[2]['content'])
        # TODO END

        os_info = get_os_info()
        os_specific_techologies = self.convo_os_specific_tech.send_message('development/env_setup/specs.prompt',
            { "os_info": os_info, "technologies": self.project.architecture }, FILTER_OS_TECHNOLOGIES)

        for technology in os_specific_techologies:
            llm_response = self.convo_os_specific_tech.send_message('development/env_setup/install_next_technology.prompt',
                { 'technology': technology}, {
                    'definitions': [{
                        'name': 'execute_command',
                        'description': f'Executes a command that should check if {technology} is installed on the machine. ',
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'command': {
                                    'type': 'string',
                                    'description': f'Command that needs to be executed to check if {technology} is installed on the machine.',
                                },
                                'timeout': {
                                    'type': 'number',
                                    'description': f'Timeout in seconds for the approcimate time this command takes to finish.',
                                }
                            },
                            'required': ['command', 'timeout'],
                        },
                    }],
                    'functions': {
                        'execute_command': execute_command_and_check_cli_response
                    },
                    'send_convo': True
                })
            
            if not llm_response == 'DONE':
                installation_commands = self.convo_os_specific_tech.send_message('development/env_setup/unsuccessful_installation.prompt',
                    { 'technology': technology }, EXECUTE_COMMANDS)
                if installation_commands is not None:
                    for cmd in installation_commands:
                        run_command_until_success(cmd['command'], cmd['timeout'], self.convo_os_specific_tech)

        logger.info('The entire tech stack neede is installed and ready to be used.')

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "os_specific_techologies": os_specific_techologies, "newly_installed_technologies": [], "app_data": generate_app_data(self.project.args)
        })

        # ENVIRONMENT SETUP END

    def implement_code_changes(self, code_changes_description):
        code_monkey = CodeMonkey(self.project, self)
        code_monkey.implement_code_changes(code_changes_description)

    def test_code_changes(self, code_monkey, convo):
        (test_type, command, automated_test_description, manual_test_description) = convo.send_message('development/task/step_check.prompt', {}, GET_TEST_TYPE)
        
        if test_type == 'command_test':
            run_command_until_success(command['command'], command['timeout'], convo)
        elif test_type == 'automated_test':
            code_monkey.implement_test(convo, automated_test_description)
        elif test_type == 'manual_test':
            # TODO make the message better
            self.project.ask_for_human_verification(
                'Message from Euclid: I need your help. Can you please test if this was successful?',
                manual_test_description
            )

    def implement_step(self, convo, step_index, type, description):
        # TODO remove hardcoded folder path
        directory_tree = self.project.get_directory_tree()
        step_details = convo.send_message('development/task/next_step.prompt', {
            'finished_steps': [],
            'step_description': description,
            'step_type': type,
            'directory_tree': directory_tree,
            'step_index': step_index
        }, EXECUTE_COMMANDS);
        if type == 'COMMAND':
            for cmd in step_details:
                run_command_until_success(cmd['command'], cmd['timeout'], convo)
        elif type == 'CODE_CHANGE':
            code_changes_details = get_step_code_changes()
            # TODO: give to code monkey for implementation
        pass
