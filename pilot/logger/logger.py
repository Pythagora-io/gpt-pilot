import os
import re
import logging


def setup_logger():
    # Create a custom format for your logs
    log_format = "%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() ] %(levelname)s: %(message)s"

    # Create a log handler for file output
    file_handler = logging.FileHandler(
        filename=os.path.join(os.path.dirname(__file__), 'debug.log'),
        mode='w',
        encoding='utf-8',
    )

    # Apply the custom format to the handler
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    # file_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    file_handler.addFilter(filter_sensitive_fields)

    # Create a logger and add the handler
    logger = logging.getLogger()
    logger.addHandler(file_handler)

    if os.getenv('DEBUG') == 'true':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return logger


sensitive_fields = ['--api-key', 'password']


def filter_sensitive_fields(record):
    # TODO: also remove escape sequences for colors, bold etc
    if isinstance(record.args, dict):  # check if args is a dictionary
        args = record.args.copy()
        for field in sensitive_fields:
            if field in args:
                args[field] = '*****'
        record.args = args

    elif isinstance(record.args, tuple):  # check if args is a tuple
        args_list = list(record.args)
        # Convert the tuple to a list and replace sensitive fields
        args_list = ['*****' if arg in sensitive_fields else arg for arg in args_list]
        record.args = tuple(args_list)

    # Remove ANSI escape sequences - colours & bold
    # Peewee passes a tuple as record.msg
    if isinstance(record.msg, str):
        record.msg = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', record.msg)

    return True


logger = setup_logger()
