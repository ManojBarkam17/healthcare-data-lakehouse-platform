"""Structured logging setup with loguru (falls back to stdlib logging)."""

import logging
import sys

try:
    from loguru import logger

    # Remove default handler and add custom format
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    _USE_LOGURU = True
except ImportError:
    _USE_LOGURU = False


def get_logger(name: str):
    """Return a logger bound with a module name."""
    if _USE_LOGURU:
        return logger.bind(name=name)
    _logger = logging.getLogger(name)
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s - %(message)s")
        )
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
    return _logger
