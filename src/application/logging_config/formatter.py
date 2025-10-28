import logging

from uvicorn.logging import DefaultFormatter

from application.settings import ON_WINDOWS


class CustomFormatter(DefaultFormatter):

    LOG_FORMAT: str = "%(levelname)-8s | %(asctime)s | %(module_path)-20s | %(message)s"

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    blue = "\x1b[34;20m"
    green = "\x1b[32;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: blue + LOG_FORMAT + reset,
        logging.INFO: green + "%(levelname)-8s" + reset + " | %(asctime)s | %(module_path)-20s | %(message)s",
        logging.WARNING: yellow + LOG_FORMAT + reset,
        logging.ERROR: red + LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + LOG_FORMAT + reset
    }

    def format(self, record):
        if False and ON_WINDOWS:
            # On Windows, remove color codes
            log_fmt = self.LOG_FORMAT
        else:
            log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
