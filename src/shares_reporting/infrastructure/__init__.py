"""Infrastructure layer for shares reporting.

Contains external concerns like configuration management,
file I/O, database access, and third-party integrations.
"""

from .config import (
    Config,
    ConversionRate,
    initialize_default_configuration_file,
    load_configuration_from_file,
)

__all__ = [
    "Config",
    "load_configuration_from_file",
    "initialize_default_configuration_file",
    "ConversionRate",
]
