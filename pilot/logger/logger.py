import os
import logging


def setup_logger():
    # Create a custom format for your logs
    log_format = "%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() ] %(levelname)s: %(message)s"

    # Create a log handler for file output
    file_handler = logging.FileHandler(filename=os.path.join(os.path.dirname(__file__), 'debug.log'), mode='w')

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
    if len(record.args):
        args = record.args.copy()

        for field in sensitive_fields:
            if field in args:
                args[field] = '*****'

        record.args = args
    return record.levelno <= logging.INFO


logger = setup_logger()
