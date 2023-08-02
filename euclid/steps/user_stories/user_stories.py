# user_stories.py
import json
from termcolor import colored
from helpers.AgentConvo import AgentConvo

from utils.utils import execute_step, find_role_from_step, generate_app_data, step_already_finished
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user
from const.function_calls import USER_STORIES


def get_user_stories(prompt, args):
    current_step = 'user_stories'
    convo_user_stories = AgentConvo(current_step)

    # If this app_id already did this step, just get all data from DB and don't ask user again
    step = get_progress_steps(args['app_id'], current_step)
    if step and not execute_step(args['step'], current_step):
        step_already_finished(args, step)
        return step['user_stories'], step['messages']

    # USER STORIES
    print(colored(f"Generating user stories...\n", "green"))
    logger.info(f"Generating user stories...")

    user_stories = convo_user_stories.send_message('user_stories/specs.prompt',
                                                   {'prompt': prompt, 'app_type': args['app_type']},
                                                   USER_STORIES)

    logger.info(user_stories)
    user_stories = get_additional_info_from_user(user_stories, 'product_owner')

    logger.info(f"Final user stories: {user_stories}")

    save_progress(args['app_id'], current_step, {
        "messages": convo_user_stories.get_messages(),
        "user_stories": user_stories,
        "app_data": generate_app_data(args)
    })

    return user_stories, convo_user_stories
    # USER STORIES END
