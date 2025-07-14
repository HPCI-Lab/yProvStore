import logging
import os
from dataclasses import dataclass, asdict, field

from application.settings import LOG_LEVEL


class LastPartFilter(logging.Filter):
    def filter(self, record):
        cwd = os.getcwd()
        module_path = []
        split_path = record.pathname[len(cwd)::].rsplit('\\')
        for split in split_path:
            module_path.append(split.lower())
        module_path[-1] = module_path[-1].split(".")[0]
        module_path = module_path[1:]
        record.module_path = ".".join(module_path)
        return True


@dataclass
class LogConfig:
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "logger"
    LOG_LEVEL: str = LOG_LEVEL

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = field(default_factory=lambda: {
        "default": {
            "()": "application.logging_config.formatter.CustomFormatter",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    })
    handlers: dict = field(default_factory=lambda: {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "filters": [LastPartFilter()],
        },
    })
    loggers: dict = field(default_factory=lambda: {
        "": {"handlers": ["default"], "level": LOG_LEVEL},
    })


def configure_logging() -> None:
    """Configure logging for the application."""
    logging.config.dictConfig(asdict(LogConfig()))
