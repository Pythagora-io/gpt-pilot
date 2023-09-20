import os
import logging


def setup_logger():
    # Create a custom format for your logs
    log_format = "%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() ] %(levelname)s: %(message)s"

    # Create a log handler for file output
    file_handler = logging.FileHandler(filename=os.path.join(os.path.dirname(__file__), 'debug.log'), mode='w')
    file_handler.setLevel(logging.DEBUG)

    # Apply the custom format to the handler
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    # Create a logger and add the handler
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
