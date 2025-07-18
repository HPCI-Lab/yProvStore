import os
import logging

from uvicorn.logging import DefaultFormatter

from application.settings import ON_WINDOWS


class CustomFormatter(DefaultFormatter):

    LOG_FORMAT: str = "%(levelname)-6s | %(asctime)s | %(module_path)s | %(message)s"

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    blue = "\x1b[34;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: blue + LOG_FORMAT + reset,
        logging.INFO: grey + LOG_FORMAT + reset,
        logging.WARNING: yellow + LOG_FORMAT + reset,
        logging.ERROR: red + LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + LOG_FORMAT + reset
    }

    def format(self, record):
        if ON_WINDOWS:
            # On Windows, remove color codes
            log_fmt = self.LOG_FORMAT
        else:
            log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
