"""
Logging configuration for QmanAssist.
Uses loguru for structured, colorized logging.
"""

import sys
from pathlib import Path
from loguru import logger

from config.settings import get_settings


def setup_logging(log_level: str = None) -> None:
    """Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  If None, uses setting from config.
    """
    settings = get_settings()
    log_level = log_level or settings.log_level

    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # File handler for all logs
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "qmanassist.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    # Separate error log
    logger.add(
        log_dir / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip",
    )

    logger.info(f"Logging initialized at {log_level} level")


def get_logger(name: str):
    """Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logger.bind(name=name)
