"""Shares Reporting Tool.

A financial application that processes Interactive Brokers CSV reports
to generate tax reporting data for Portugal.

This package provides tools for:
- Parsing Interactive Brokers CSV files
- Matching buy/sell transactions using FIFO within daily buckets
- Calculating capital gains with currency conversion
- Generating Excel reports with formulas.
"""

__version__ = "0.0.1"
__author__ = "Andrey Dmitriev <dmitriev.andrey.vitalyevich@gmail.com>"

from .application.extraction import *
from .application.persisting import *
from .application.transformation import *
from .domain.accumulators import *
from .domain.collections import *
from .domain.entities import *
from .domain.value_objects import *
from .infrastructure.config import *

__all__ = [
    # Value Objects
    "TradeDate",
    "parse_trade_date",
    "TradeType",
    "Currency",
    "parse_currency",
    "Company",
    "parse_company",
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
    "parse_ib_export_all",
    "parse_ib_export",
    "parse_dividend_income",
    "calculate_fifo_gains",
    "export_rollover_file",
    "generate_tax_report",
    "load_configuration_from_file",
    "Config",
]
