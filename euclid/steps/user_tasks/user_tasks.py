# user_tasks.py
import json
from termcolor import colored
from helpers.AgentConvo import AgentConvo

from utils.utils import execute_step, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user
from const.function_calls import USER_TASKS


def get_user_tasks(convo, args):
    current_step = 'user_tasks'

    # If this app_id already did this step, just get all data from DB and don't ask user again
    steps = get_progress_steps(args['app_id'], current_step)
    if steps and not execute_step(args['step'], current_step):
        first_step = steps[0]
        data = json.loads(first_step['data'])

        app_data = data.get('app_data')
        if app_data is not None:
            args.update(app_data)

        message = f"User tasks already done for this app_id: {args['app_id']}. Moving to next step..."
        print(colored(message, "green"))
        logger.info(message)
        return data.get('user_tasks'), data.get('messages')

    # USER TASKS
    print(colored(f"Generating user tasks...\n", "green"))
    logger.info(f"Generating user tasks...")

    user_tasks = convo.send_message('user_stories/user_tasks.prompt',
                                       {}, USER_TASKS)

    logger.info(user_tasks)
    user_tasks = get_additional_info_from_user(user_tasks, 'product_owner')

    logger.info(f"Final user tasks: {user_tasks}")

    save_progress(args['app_id'], current_step, {
        "messages": convo.get_messages(),"user_tasks": user_tasks, "app_data": generate_app_data(args)
    })

    return user_tasks
    # USER TASKS END