# main.py
from __future__ import print_function, unicode_literals

from dotenv import load_dotenv

from utils.utils import get_arguments
from logger.logger import logger

from steps.project_description.project_description import get_project_description
from steps.user_stories.user_stories import get_user_stories
from steps.user_tasks.user_tasks import get_user_tasks
from steps.architecture.architecture import get_architecture


def init():
    load_dotenv()

    arguments = get_arguments()

    logger.info(f"Starting with args: {arguments}")

    return arguments


if __name__ == "__main__":
    args = init()

    high_level_summary, high_level_messages = get_project_description(args)

    user_stories, user_stories_messages = get_user_stories(high_level_summary, args)

    user_tasks, user_tasks_messages = get_user_tasks(user_stories_messages, args)

    architecture, architecture_messages = get_architecture(high_level_summary, user_stories, user_tasks, args)

    # development
