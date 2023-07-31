from utils.llm_connection import get_prompt, create_gpt_chat_completion
from utils.utils import get_sys_message, find_role_from_step, capitalize_first_word_with_underscores
from logger.logger import logger
from termcolor import colored



class AgentConvo:
    messages = []

    def __init__(self, high_level_step):
        self.high_level_step = high_level_step
        self.agent = find_role_from_step(high_level_step)

        # add system message
        self.messages.append(get_sys_message(self.agent))

    def send_message(self, prompt_path, prompt_data, function_calls=None):
        # craft message
        prompt = get_prompt(prompt_path, prompt_data)
        self.messages.append({"role": "user", "content": prompt})

        response = create_gpt_chat_completion(self.messages, self.high_level_step, function_calls=function_calls)
        
        # TODO handle errors from OpenAI
        if response == {}:
            raise Exception("OpenAI API error happened.")       

        response = self.postprocess_response(response, function_calls)
        
        # TODO remove this once the database is set up properly
        message_content = response
        if isinstance(response, list):
            if isinstance(response[0], dict):
                string_response = [
                    f'#{i + 1}\n' + '\n'.join([f'{key}: {value}' for key, value in d.items()])
                    for i, d in enumerate(response)
                ]
            else:
                string_response = ['- ' + r for r in response]

            message_content = '\n'.join(string_response)
        # TODO END

        
        # TODO we need to specify the response when there is a function called
        # TODO maybe we can have a specific function that creates the GPT response from the function call
        self.messages.append({"role": "assistant", "content": message_content}) 
        self.log_message(message_content)

        return response
    
    def get_messages(self):
        return self.messages
    
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