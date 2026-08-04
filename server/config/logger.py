import logging
import sys


def setup_logger(name: str = "app", log_level: str | None = None) -> logging.Logger:
    """Configures and returns a structured standard logger."""
    if log_level is None:
        from config.settings import get_settings
        log_level = get_settings().LOG_LEVEL

    logger = logging.getLogger(name)
    logger.setLevel(log_level.upper() if isinstance(log_level, str) else log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(name: str = "app", log_level: str | None = None) -> logging.Logger:
    """Helper function to get or create a logger with a custom name."""
    return setup_logger(name=name, log_level=log_level)



