"""
utils/logger.py
===============
Centralised logging configuration for the FloodShield-Zambia AI Engine.

Why Loguru?
-----------
Loguru replaces Python's stdlib logging with a simpler, more expressive API.
It supports structured logging, file rotation, coloured console output, and
exception tracebacks out of the box — all of which improve debugging in a
machine learning workflow.

Usage
-----
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Training started")
    logger.warning("Missing values detected: {count}", count=5)
    logger.error("Model failed to converge")
"""

import sys
from pathlib import Path

from loguru import logger as _loguru_logger

from src.config.settings import settings

# ---------------------------------------------------------------------------
# Remove the default Loguru handler (we set up our own below).
# ---------------------------------------------------------------------------
_loguru_logger.remove()

# ---------------------------------------------------------------------------
# Console handler — coloured, human-readable output during development.
# ---------------------------------------------------------------------------
_loguru_logger.add(
    sys.stderr,
    level="INFO",
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
)

# ---------------------------------------------------------------------------
# File handler — rotating log file, retained for 30 days.
# ---------------------------------------------------------------------------
_log_file: Path = settings.logs_dir / "floodshield_{time:YYYY-MM-DD}.log"
_loguru_logger.add(
    str(_log_file),
    level="DEBUG",
    rotation="00:00",        # New file at midnight
    retention="30 days",
    compression="zip",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | {message}"
    ),
    enqueue=True,            # Thread-safe logging
    backtrace=True,          # Full exception tracebacks
    diagnose=False,          # Disable variable inspection in production
)


def get_logger(name: str):
    """
    Return a module-scoped Loguru logger bound with the module name.

    Parameters
    ----------
    name : str
        Typically ``__name__`` from the calling module.

    Returns
    -------
    loguru.Logger
        A logger instance bound with ``name`` as a context variable.

    Example
    -------
    >>> logger = get_logger(__name__)
    >>> logger.info("Pipeline started")
    """
    return _loguru_logger.bind(name=name)
