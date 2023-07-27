# main_old.py
from __future__ import print_function, unicode_literals

import uuid
import json
from dotenv import load_dotenv
from termcolor import colored

from utils.utils import get_arguments, execute_step, split_into_bullets, find_role_from_step
from database.database import save_progress, save_app, get_progress_steps
from logger.logger import logger
from prompts.prompts import ask_for_app_type, ask_for_main_app_definition, get_additional_info_from_openai, \
    get_additional_info_from_user, generate_messages_from_description, execute_chat_prompt
from utils.llm_connection import get_prompt


def init():
    load_dotenv()

    arguments = get_arguments()

    logger.info(f"Starting with args: {arguments}")

    return arguments


def get_project_description(args):
    current_step = 'project_summary'
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

        return summary

    # PROJECT DESCRIPTION
    app_type = ask_for_app_type()

    save_app(args['user_id'], args['app_id'], app_type)

    description = ask_for_main_app_definition()

    high_level_messages = get_additional_info_from_openai(generate_messages_from_description(description, app_type))

    high_level_summary = execute_chat_prompt('utils/summary.prompt',
                                             {'conversation': '\n'.join(
                                                 [f"{msg['role']}: {msg['content']}" for msg in high_level_messages])},
                                             current_step)

    app_data = {'app_id': args['app_id'], 'app_type': app_type}
    args['app_type'] = app_type

    save_progress(args['app_id'], current_step,
                  {"messages": high_level_messages, "summary": high_level_summary, "app_data": app_data})

    return high_level_summary
    # PROJECT DESCRIPTION END


def get_user_stories(summary, args):
    current_step = 'user_stories'
    role = find_role_from_step(current_step)
    # If this app_id already did this step, just get all data from DB and don't ask user again
    steps = get_progress_steps(args['app_id'], current_step)
    if steps and not execute_step(args['step'], current_step):
        first_step = steps[0]
        data = json.loads(first_step['data'])

        summary = data.get('summary')
        app_data = data.get('app_data')
        args.update(app_data)

        message = f"User stories already done for this app_id: {args['app_id']}. Moving to next step..."
        print(colored(message, "green"))
        logger.info(message)
        return summary, args

    # USER STORIES
    print(colored(f"Generating user stories...\n", "green"))
    logger.info(f"Generating user stories...")

    user_stories = execute_chat_prompt('user_stories/specs.prompt',
                                       {'summary': summary, 'app_type': args['app_type']},
                                       current_step)

    logger.info(split_into_bullets(user_stories))
    user_stories = get_additional_info_from_user(split_into_bullets(user_stories), role)

    logger.info(f"Final user stories: {user_stories}")

    save_progress(args['app_id'], current_step, {"user_stories": user_stories})

    return user_stories
    # USER STORIES END


if __name__ == "__main__":
    args = init()

    high_level_summary = get_project_description(args)

    user_stories = get_user_stories(high_level_summary, args)

    # get architecture plan

    # development
