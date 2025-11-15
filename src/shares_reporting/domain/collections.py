from typing import Dict, List, NamedTuple

from .entities import (
    QuantitatedTradeAction,
    TradeCycle,
    CapitalGainLine,
    CurrencyCompany,
    DividendIncomePerSecurity,
)
from .value_objects import TradeDate, Currency
from .accumulators import TradePartsWithinDay
from .value_objects import TradeType


# Type aliases for collections
QuantitatedTradeActions = List[QuantitatedTradeAction]
CapitalGainLines = List[CapitalGainLine]
SortedDateRanges = List[TradeDate]
TradeCyclePerCompany = Dict[CurrencyCompany, TradeCycle]
CapitalGainLinesPerCompany = Dict[CurrencyCompany, CapitalGainLines]

# Additional collection types from the original domain.py
DayPartitionedTrades = Dict[TradeDate, TradePartsWithinDay]
PartitionedTradesByType = Dict[TradeType, DayPartitionedTrades]


class CurrencyToCoordinate(NamedTuple):
    currency: Currency
    coordinate: str


CurrencyToCoordinates = List[CurrencyToCoordinate]

# Type aliases for dividend income collections
DividendIncomePerSecurityList = List[DividendIncomePerSecurity]
DividendIncomePerCompany = Dict[
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
