# user_tasks.py
import json
from termcolor import colored

from utils.utils import execute_step, find_role_from_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from prompts.prompts import get_additional_info_from_user, execute_chat_prompt
from const.function_calls import USER_TASKS


def get_user_tasks(previous_messages, args):
    current_step = 'user_tasks'
    role = find_role_from_step(current_step)
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

    # TODO: remove this once the database is set up properly
    previous_messages[2]['content'] = '\n'.join(previous_messages[2]['content'])
    # TODO END
    user_tasks, user_tasks_messages = execute_chat_prompt('user_stories/user_tasks.prompt',
                                       {}, current_step, previous_messages, function_calls=USER_TASKS)

    logger.info(user_tasks)
    user_tasks = get_additional_info_from_user(user_tasks, role)

    logger.info(f"Final user tasks: {user_tasks}")

    save_progress(args['app_id'], current_step, {
        "messages": user_tasks_messages,"user_tasks": user_tasks, "app_data": generate_app_data(args)
    })

    return user_tasks, user_tasks_messages
    # USER TASKS END