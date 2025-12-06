"""Extraction package for shares reporting.

Provides functionality to parse Interactive Brokers CSV exports,
extracting trades, dividends, and withholding taxes using a
state-machine based parser.
"""

from __future__ import annotations

from .processing import (
    parse_dividend_income,
    parse_ib_export,
    parse_ib_export_all,
)

__all__ = ["parse_dividend_income", "parse_ib_export", "parse_ib_export_all"]
