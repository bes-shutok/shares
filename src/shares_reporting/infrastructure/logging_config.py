"""Logging configuration for the shares reporting application.

Provides centralized logging setup with appropriate log levels,
formatters, and handlers for different environments.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_application_logging(
    level: str = "INFO", log_file: Path | None = None, enable_console: bool = True
) -> None:
    """Configure application logging with standardized formatting and output options.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for persistent logging
        enable_console: Whether to enable console output for real-time monitoring
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Add console handler if enabled
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets all levels
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def create_module_logger(name: str) -> logging.Logger:
    """Create standardized logger for specific module with consistent configuration.

    Args:
        name: Logger name (typically __name__ for module-level logging)

    Returns:
        Configured logger instance ready for use
    """
    return logging.getLogger(name)
