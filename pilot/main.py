# main.py
from __future__ import print_function, unicode_literals

import sys

from dotenv import load_dotenv
from termcolor import colored
load_dotenv()

from helpers.Project import Project

from utils.arguments import get_arguments
from utils.exit import exit_gpt_pilot
from logger.logger import logger
from database.database import database_exists, create_database, tables_exist, create_tables


def init():
    # Check if the "euclid" database exists, if not, create it
    if not database_exists():
        create_database()

    # Check if the tables exist, if not, create them
    if not tables_exist():
        create_tables()

    arguments = get_arguments()

    logger.info(f"Starting with args: {arguments}")

    return arguments


if __name__ == "__main__":
    try:
        args = init()
        project = Project(args)
        project.start()
    except KeyboardInterrupt:
        exit_gpt_pilot()
    except Exception as e:
        print(colored('---------- GPT PILOT EXITING WITH ERROR ----------', 'red'))
        print(colored(e, 'red'))
        print(colored('--------------------------------------------------', 'red'))
        exit_gpt_pilot()
    finally:
        sys.exit(0)
