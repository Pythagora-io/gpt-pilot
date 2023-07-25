# main_old.py
from __future__ import print_function, unicode_literals

import uuid
from dotenv import load_dotenv

from database.database import save_progress, save_app
from logger.logger import logger
from prompts.prompts import ask_for_app_type,ask_for_main_app_definition, get_additional_info_from_openai,\
    generate_messages_from_description, execute_chat_prompt


if __name__ == "__main__":
    logger.info('Starting')
    load_dotenv()

    app_type = ask_for_app_type()

    user_id = str(uuid.uuid4())
    app_id = save_app(user_id, app_type)

    description = ask_for_main_app_definition()

    messages = get_additional_info_from_openai(generate_messages_from_description(description, app_type))

    summary = execute_chat_prompt('summary.pt',
                                  {'conversation': '\n'.join([f"{msg['role']}: {msg['content']}" for msg in messages])},
                                  'summarize',
                                  'Project summary')

    save_progress(app_id, 'main_description', {"messages": messages, "summary": summary})

    stories = execute_chat_prompt('user_stories.pt',
                                  {'summary': summary, 'app_type': app_type},
                                  'user_stories',
                                  'User stories')
