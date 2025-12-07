"""Value objects for the domain layer."""

import calendar
from datetime import datetime
from enum import Enum
from typing import NamedTuple

from .constants import CURRENCY_CODE_LENGTH
from .exceptions import DataValidationError


class TradeDate(NamedTuple):
    """Represents a date associated with a trade."""

    year: int
    month: int
    day: int

    def get_month_name(self) -> str:
        """Get the full name of the month."""
        return calendar.month_name[self.month]

    def __repr__(self) -> str:
        """Return string representation."""
        return "[" + str(self.day) + " " + calendar.month_name[self.month] + ", " + str(self.year) + "]"

    def to_datetime(self) -> datetime:
        """Convert TradeDate to datetime object with UTC timezone."""
        return datetime(self.year, self.month, self.day, 0, 0, tzinfo=UTC)


def parse_trade_date(date: datetime) -> TradeDate:
    """Parse TradeDate value object from datetime."""
    return TradeDate(date.year, date.month, date.day)


class TradeType(Enum):
    """Enumeration of trade types."""

    BUY = 1
    SELL = 2


class Currency(NamedTuple):
    """Value object representing a currency."""

    currency: str


def parse_currency(currency: str) -> Currency:
    """Parse validated Currency value object from string code."""
    if len(currency) != CURRENCY_CODE_LENGTH:
        raise DataValidationError(
            f"Currency is expected to be a length of {CURRENCY_CODE_LENGTH}, instead got [{currency}]!"
        )
    return Currency(currency.upper())


class Company(NamedTuple):
    """Value object representing a company/security."""

    ticker: str
    isin: str = ""
    country_of_issuance: str = "Unknown"


def parse_company(ticker: str, isin: str = "", country_of_issuance: str = "Unknown") -> Company:
    """Parse Company value object with ticker and optional ISIN/country data."""
    if len(ticker) == 0:
        raise DataValidationError("Company is expected to be not empty, instead got empty string!")
    # Not just uppercase because IB sometimes use abridgements like TKAd (Thyssen-Krupp Ag deutsch?)
    return Company(ticker, isin, country_of_issuance)
