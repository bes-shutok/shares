"""
Shares Reporting Tool

A financial application that processes Interactive Brokers CSV reports
to generate tax reporting data for Portugal.

This package provides tools for:
- Parsing Interactive Brokers CSV files
- Matching buy/sell transactions using FIFO within daily buckets
- Calculating capital gains with currency conversion
- Generating Excel reports with formulas
"""

__version__ = "0.0.1"
__author__ = "Andrey Dmitriev <dmitriev.andrey.vitalyevich@gmail.com>"

from .domain.value_objects import *
from .domain.entities import *
from .domain.accumulators import *
from .domain.collections import *
from .application.extraction import *
from .application.transformation import *
from .application.persisting import *
from .infrastructure.config import *

__all__ = [
    # Value Objects
    "TradeDate",
    "get_trade_date",
    "TradeType",
    "Currency",
    "get_currency",
    "Company",
    "get_company",
    # Entities
    "TradeAction",
    "QuantitatedTradeAction",
    "TradeCycle",
    "CurrencyCompany",
    "CapitalGainLine",
    "DividendIncomePerSecurity",
    # Accumulators
    "CapitalGainLineAccumulator",
    "TradePartsWithinDay",
    # Collections and Type Aliases
    "QuantitatedTradeActions",
    "CapitalGainLines",
    "SortedDateRanges",
    "TradeCyclePerCompany",
    "CapitalGainLinesPerCompany",
    "DayPartitionedTrades",
    "PartitionedTradesByType",
    "CurrencyToCoordinate",
    "CurrencyToCoordinates",
    "DividendIncomePerSecurityList",
    "DividendIncomePerCompany",
    # Functions from each module
    "parse_data",
    "calculate",
    "persist_results",
    "persist_leftover",
    "read_config",
    "create_config",
    "extract_dividend_income",
]
