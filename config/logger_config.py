import logging
import sys


def setup_logging():
    # Configure logger
    logger = logging.getLogger("TelegramBotLogger")
    logger.setLevel(logging.DEBUG)  # Set to lowest level to capture all logs

    # Configure stream handlers for different log levels
    # Debug handler
    debug_handler = logging.StreamHandler(sys.stdout)
    debug_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    debug_handler.setFormatter(debug_formatter)
    debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG)

    # Info handler
    info_handler = logging.StreamHandler(sys.stdout)
    info_handler.setLevel(logging.INFO)
    info_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    info_handler.setFormatter(info_formatter)
    info_handler.addFilter(lambda record: record.levelno == logging.INFO)

    # Error handler
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s\n%(pathname)s:%(lineno)d"
    )
    error_handler.setFormatter(error_formatter)
    error_handler.addFilter(lambda record: record.levelno >= logging.ERROR)

    warning_handler = logging.StreamHandler(sys.stdout)
    warning_handler.setLevel(logging.WARNING)
    warning_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    warning_handler.setFormatter(warning_formatter)
    warning_handler.addFilter(lambda record: record.levelno >= logging.WARNING)

    # Attach handlers to logger if not already present
    if not logger.handlers:
        logger.addHandler(debug_handler)
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        logger.addHandler(warning_handler)
    return logger


# Initialize the logger
logger = setup_logging()
