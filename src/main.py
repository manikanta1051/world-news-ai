from src.common.config import settings
from src.common.logging_config import logger


def start_application() -> None:
    """Start the World News AI application."""

    logger.info(
        "Starting %s in %s environment",
        settings.app_name,
        settings.app_env,
    )

    logger.info("Configuration system loaded successfully")
    logger.info("Logging system loaded successfully")


if __name__ == "__main__":
    start_application()