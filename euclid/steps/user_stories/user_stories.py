# user_stories.py
import json
from termcolor import colored

from utils.utils import execute_step, split_into_bullets, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user, execute_chat_prompt
from const.function_calls import USER_STORIES


def get_user_stories(summary, args):
    current_step = 'user_stories'
    role = find_role_from_step(current_step)
    # If this app_id already did this step, just get all data from DB and don't ask user again
    steps = get_progress_steps(args['app_id'], current_step)
    if steps and not execute_step(args['step'], current_step):
        first_step = steps[0]
        data = json.loads(first_step['data'])

        user_stories = data.get('user_stories')
        app_data = data.get('app_data')
        if app_data is not None:
            args.update(app_data)

        message = f"User stories already done for this app_id: {args['app_id']}. Moving to next step..."
        print(colored(message, "green"))
        logger.info(message)
        return user_stories, data.get('messages')

    # USER STORIES
    print(colored(f"Generating user stories...\n", "green"))
    logger.info(f"Generating user stories...")

    user_stories, user_stories_messages = execute_chat_prompt('user_stories/specs.prompt',
                                        {'prompt': summary, 'app_type': args['app_type']},
                                        current_step,
                                        function_calls=USER_STORIES)

    logger.info(user_stories)
    user_stories = get_additional_info_from_user(user_stories, role)

    logger.info(f"Final user stories: {user_stories}")

    save_progress(args['app_id'], current_step, {
        "messages": user_stories_messages, "user_stories": user_stories, "app_data": generate_app_data(args)
    })

    return user_stories, user_stories_messages
    # USER STORIES END