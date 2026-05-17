"""Structured logging setup using loguru."""

import sys

from loguru import logger

# Remove default handler and add custom format
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)


def get_logger(name: str) -> "logger":
    """Return a logger bound with a module name."""
    return logger.bind(name=name)
