# project_description.py
import json
from termcolor import colored
from helpers.AgentConvo import AgentConvo

from logger.logger import logger
from database.database import save_progress, save_app, get_progress_steps
from utils.utils import execute_step, generate_app_data
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, get_additional_info_from_openai, \
    generate_messages_from_description


def get_project_description(args):
    current_step = 'project_description'
    convo_project_description = AgentConvo(current_step)

    # If this app_id already did this step, just get all data from DB and don't ask user again
    steps = get_progress_steps(args['app_id'], current_step)
    if steps and not execute_step(args['step'], current_step):
        first_step = steps[0]
        data = json.loads(first_step['data'])

        summary = data.get('summary')
        app_data = data.get('app_data')
        args.update(app_data)

        message = f"Project summary already done for this app_id: {args['app_id']}. Moving to next step..."
        print(colored(message, "green"))
        logger.info(message)

        return summary, data.get('messages')

    # PROJECT DESCRIPTION
    args['app_type'] = ask_for_app_type()

    save_app(args['user_id'], args['app_id'], args['app_type'])

    description = ask_for_main_app_definition()

    high_level_messages = get_additional_info_from_openai(
        generate_messages_from_description(description, args['app_type']))

    high_level_summary = convo_project_description.send_message('utils/summary.prompt',
                                             {'conversation': '\n'.join(
                                                 [f"{msg['role']}: {msg['content']}" for msg in high_level_messages])})

    save_progress(args['app_id'], current_step,
                  {"messages": high_level_messages, "summary": high_level_summary, "app_data": generate_app_data(args)
                   })

    return high_level_summary, high_level_messages
    # PROJECT DESCRIPTION END
