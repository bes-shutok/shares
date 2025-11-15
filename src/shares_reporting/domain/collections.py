from typing import NamedTuple

from .accumulators import TradePartsWithinDay
from .entities import (
    CapitalGainLine,
    CurrencyCompany,
    DividendIncomePerSecurity,
    QuantitatedTradeAction,
    TradeCycle,
)
from .value_objects import Currency, TradeDate, TradeType

# Type aliases for collections
QuantitatedTradeActions = list[QuantitatedTradeAction]
CapitalGainLines = list[CapitalGainLine]
SortedDateRanges = list[TradeDate]
TradeCyclePerCompany = dict[CurrencyCompany, TradeCycle]
CapitalGainLinesPerCompany = dict[CurrencyCompany, CapitalGainLines]

# Additional collection types from the original domain.py
DayPartitionedTrades = dict[TradeDate, TradePartsWithinDay]
PartitionedTradesByType = dict[TradeType, DayPartitionedTrades]


class CurrencyToCoordinate(NamedTuple):
    currency: Currency
    coordinate: str


CurrencyToCoordinates = list[CurrencyToCoordinate]

# Type aliases for dividend income collections
DividendIncomePerSecurityList = list[DividendIncomePerSecurity]
DividendIncomePerCompany = dict[
    str, DividendIncomePerSecurity
]  # symbol -> DividendIncomePerSecurity


class IBExportData:
    """Container for all data extracted from an Interactive Brokers export file."""

    def __init__(
        self, trade_cycles: TradeCyclePerCompany, dividend_income: DividendIncomePerCompany
    ):
        self.trade_cycles = trade_cycles
        self.dividend_income = dividend_income

    def __repr__(self) -> str:
        return (
            f"IBExportData("
            f"trade_cycles={len(self.trade_cycles)}, "
            f"dividend_income={len(self.dividend_income)})"
        )
