import logging
from pathlib import Path

from src.common.logging_config import get_log_file_path, setup_logging


def close_logger_handlers(logger: logging.Logger) -> None:
    """Close and remove every handler from a test logger."""

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_get_log_file_path_creates_parent_directory(
    tmp_path: Path,
) -> None:
    """Confirm that the log directory is created automatically."""

    log_file = tmp_path / "logs" / "test.log"

    result = get_log_file_path(str(log_file))

    assert result == log_file
    assert log_file.parent.exists()


def test_setup_logging_adds_two_handlers(
    tmp_path: Path,
) -> None:
    """Confirm that console and file handlers are configured."""

    log_file = tmp_path / "test_handlers.log"
    logger = setup_logging(
        logger_name="test_handlers_logger",
        log_file=str(log_file),
    )

    assert len(logger.handlers) == 2

    close_logger_handlers(logger)


def test_log_message_is_written_to_file(
    tmp_path: Path,
) -> None:
    """Confirm that a log message is saved to the file."""

    log_file = tmp_path / "test_output.log"
    logger = setup_logging(
        logger_name="test_output_logger",
        log_file=str(log_file),
    )

    logger.info("Logging test completed successfully")

    for handler in logger.handlers:
        handler.flush()

    log_content = log_file.read_text(encoding="utf-8")

    assert "Logging test completed successfully" in log_content
    assert "INFO" in log_content

    close_logger_handlers(logger)


def test_duplicate_handlers_are_not_added(
    tmp_path: Path,
) -> None:
    """Confirm that repeated setup does not add duplicate handlers."""

    log_file = tmp_path / "test_duplicate.log"
    logger_name = "test_duplicate_logger"

    first_logger = setup_logging(
        logger_name=logger_name,
        log_file=str(log_file),
    )

    second_logger = setup_logging(
        logger_name=logger_name,
        log_file=str(log_file),
    )

    assert first_logger is second_logger
    assert len(second_logger.handlers) == 2

    close_logger_handlers(second_logger)