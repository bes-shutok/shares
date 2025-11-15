import calendar
from datetime import datetime
from enum import Enum
from typing import NamedTuple

from .exceptions import DataValidationError
from .constants import CURRENCY_CODE_LENGTH, CURRENCY_FORMAT_PATTERN


class TradeDate(NamedTuple):
    year: int
    month: int
    day: int

    def get_month_name(self) -> str:
        return calendar.month_name[self.month]

    def __repr__(self) -> str:
        return (
            "["
            + str(self.day)
            + " "
            + calendar.month_name[self.month]
            + ", "
            + str(self.year)
            + "]"
        )


def get_trade_date(date: datetime) -> TradeDate:
    return TradeDate(date.year, date.month, date.day)


class TradeType(Enum):
    BUY = 1
    SELL = 2


class Currency(NamedTuple):
    currency: str


def get_currency(currency: str) -> Currency:
    if len(currency) == CURRENCY_CODE_LENGTH:
        pass
    else:
        raise DataValidationError(
            f"Currency is expected to be a length of {CURRENCY_CODE_LENGTH}, instead got [{currency}]!"
        )
    return Currency(currency.upper())


class Company(NamedTuple):
    ticker: str
    isin: str = ""
    country_of_issuance: str = "Unknown"


def get_company(ticker: str, isin: str = "", country_of_issuance: str = "Unknown") -> Company:
    if (len(ticker)) > 0:
        pass
    else:
        raise DataValidationError("Company is expected to be not empty, instead got empty string!")
    # Not just uppercase because IB sometimes use abridgements like TKAd (Thyssen-Krupp Ag deutsch?)
    return Company(ticker, isin, country_of_issuance)
