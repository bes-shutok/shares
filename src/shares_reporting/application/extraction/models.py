"""Data models and enums for the extraction process."""

from dataclasses import dataclass
from enum import Enum


class IBCsvSection(Enum):
    """Enum to track current section being processed in IB CSV file."""

    UNKNOWN = "unknown"
    FINANCIAL_INSTRUMENT = "financial_instrument"
    TRADES = "trades"
    DIVIDENDS = "dividends"
    WITHHOLDING_TAX = "withholding_tax"
    OTHER = "other"


@dataclass
class IBCsvData:
    """Container for all raw data extracted from IB CSV file."""

    security_info: dict[str, dict[str, str]]
    raw_trade_data: list[dict[str, str]]
    raw_dividend_data: list[dict[str, str]]
    raw_withholding_tax_data: list[dict[str, str]]
    metadata: dict[str, int]  # Processing statistics
