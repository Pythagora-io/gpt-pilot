import subprocess
from database.database import get_development_step_from_messages, save_development_step
from utils.utils import array_of_objects_to_string
from utils.llm_connection import get_prompt, create_gpt_chat_completion
from utils.utils import get_sys_message, find_role_from_step, capitalize_first_word_with_underscores
from logger.logger import logger
from termcolor import colored

class AgentConvo:
    def __init__(self, agent):
        self.messages = []
        self.branches = {}
        self.agent = agent
        self.high_level_step = self.agent.project.current_step

        # add system message
        self.messages.append(get_sys_message(self.agent.role))

    def send_message(self, prompt_path, prompt_data, function_calls=None):

        # craft message
        prompt = get_prompt(prompt_path, prompt_data)
        self.messages.append({"role": "user", "content": prompt})


        # check if we already have the LLM response saved
        saved_checkpoint = get_development_step_from_messages(self.agent.project.args['app_id'], self.messages)
        if saved_checkpoint is not None:
            # if we do, use it
            response = saved_checkpoint.llm_response
            self.messages = saved_checkpoint.messages
        else:
            # if we don't, get the response from LLM
            response = create_gpt_chat_completion(self.messages, self.high_level_step, function_calls=function_calls)
            save_development_step(self.agent.project.args['app_id'], self.messages, response)
        
        # TODO handle errors from OpenAI
        if response == {}:
            raise Exception("OpenAI API error happened.")       

        response = self.postprocess_response(response, function_calls)
        
        # TODO remove this once the database is set up properly
        message_content = response[0] if type(response) == tuple else response
        if isinstance(message_content, list):
            if isinstance(message_content[0], dict):
                string_response = [
                    f'#{i + 1}\n' + array_of_objects_to_string(d)
                    for i, d in enumerate(message_content)
                ]
            else:
                string_response = ['- ' + r for r in message_content]

            message_content = '\n'.join(string_response)
        # TODO END

        
        # TODO we need to specify the response when there is a function called
        # TODO maybe we can have a specific function that creates the GPT response from the function call
        self.messages.append({"role": "assistant", "content": message_content}) 
        self.log_message(message_content)

        return response

    def save_branch(self, branch_name):
        self.branches[branch_name] = self.messages.copy()

    def load_branch(self, branch_name):
        self.messages = self.branches[branch_name].copy()

    def convo_length(self):
        return len([msg for msg in self.messages if msg['role'] != 'system'])
    
    def postprocess_response(self, response, function_calls):        
        if 'function_calls' in response and function_calls is not None:
            if 'send_convo' in function_calls:
                response['function_calls']['arguments']['convo']  = self
            response = function_calls['functions'][response['function_calls']['name']](**response['function_calls']['arguments'])
        elif 'text' in response:
            response = response['text']
        
        return response
    
    def log_message(self, content):
        print_msg = capitalize_first_word_with_underscores(self.high_level_step)
        print(colored(f"{print_msg}:\n", "green"))
        print(f"{content}\n")
        logger.info(f"{print_msg}: {content}\n")

    def to_playground(self):
        with open('const/convert_to_playground_convo.js', 'r', encoding='utf-8') as file:
            content = file.read()
        process = subprocess.Popen('pbcopy', stdin=subprocess.PIPE)
        process.communicate(content.replace('{{messages}}', str(self.messages)).encode('utf-8'))