from typing import Dict, List, NamedTuple

from .entities import QuantitatedTradeAction, TradeCycle, CapitalGainLine, CurrencyCompany, DividendIncomePerSecurity
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
DividendIncomePerCompany = Dict[str, DividendIncomePerSecurity]  # symbol -> DividendIncomePerSecurity