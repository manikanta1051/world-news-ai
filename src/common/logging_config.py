import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.common.config import PROJECT_ROOT, settings


LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | "
    "%(name)s | %(filename)s:%(lineno)d | %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_log_file_path(log_file: str | None = None) -> Path:
    """Return the complete path for a log file."""

    configured_log_file = log_file or settings.log_file
    log_file_path = Path(configured_log_file)

    if not log_file_path.is_absolute():
        log_file_path = PROJECT_ROOT / log_file_path

    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    return log_file_path


def setup_logging(
    logger_name: str | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure console and rotating-file logging."""

    name = logger_name or settings.app_name
    logger = logging.getLogger(name)

    logger.setLevel(settings.log_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.log_level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=get_log_file_path(log_file),
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(settings.log_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()