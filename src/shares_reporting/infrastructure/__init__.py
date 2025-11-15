"""
Infrastructure layer for shares reporting.

Contains external concerns like configuration management,
file I/O, database access, and third-party integrations.
"""

from .config import Config, read_config, create_config, ConversionRate

__all__ = [
    "Config",
    "read_config",
    "create_config",
    "ConversionRate",
]
