"""Infrastructure layer for shares reporting.

Contains external concerns like configuration management,
file I/O, database access, and third-party integrations.
"""

from .config import (
    Config,
    ConversionRate,
    load_configuration_from_file,
)

__all__ = [
    "Config",
    "load_configuration_from_file",
    "ConversionRate",
]
