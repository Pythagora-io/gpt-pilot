# user_stories.py
import json
from termcolor import colored

from utils.utils import execute_step, split_into_bullets, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user, execute_chat_prompt


def get_architecture(high_level_summary, user_stories, user_tasks, args):
    current_step = 'architecture'
    role = find_role_from_step(current_step)
    # If this app_id already did this step, just get all data from DB and don't ask user again
    steps = get_progress_steps(args['app_id'], current_step)
    if steps and not execute_step(args['step'], current_step):
        first_step = steps[0]
        data = json.loads(first_step['data'])

        architecture = data.get('architecture')

        message = f"Architecture already done for this app_id: {args['app_id']}. Moving to next step..."
        print(colored(message, "green"))
        logger.info(message)
        return architecture, data.get('messages')

    # ARCHITECTURE
    print(colored(f"Planning project architecture...\n", "green"))
    logger.info(f"Planning project architecture...")

    architecture, architecture_messages = execute_chat_prompt('architecture/technologies.prompt',
                                                              {'prompt': high_level_summary,
                                                               'user_stories': user_stories,
                                                               'user_tasks': user_tasks,
                                                               'app_type': args['app_type']},
                                                              current_step)

    architecture = get_additional_info_from_user(split_into_bullets(architecture), role)

    logger.info(f"Final architecture: {architecture}")

    save_progress(args['app_id'], current_step, {
        "messages": architecture_messages,
        "architecture": architecture,
        "app_data": generate_app_data(args)
    })

    return architecture, architecture_messages
    # ARCHITECTURE END
