import pytest
from decimal import Decimal
from datetime import datetime

from shares_reporting.domain.collections import (
    QuantitatedTradeActions, CapitalGainLines, SortedDateRanges, TradeCyclePerCompany,
    CapitalGainLinesPerCompany, DayPartitionedTrades, PartitionedTradesByType,
    CurrencyToCoordinate, CurrencyToCoordinates
)
from shares_reporting.domain.value_objects import TradeDate, get_currency, get_company, TradeType
from shares_reporting.domain.entities import QuantitatedTradeAction, TradeAction, CapitalGainLine, TradeCycle
from shares_reporting.domain.accumulators import TradePartsWithinDay


class TestTypeAliases:
    """Test that type aliases work correctly and maintain expected behavior."""

    def test_quantitated_trade_actions_type_alias(self):
        """Test QuantitatedTradeActions type alias works as list."""
        # QuantitatedTradeActions is an alias for List[QuantitatedTradeAction]
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        quantitated = QuantitatedTradeAction(Decimal("5"), trade)

        trades: QuantitatedTradeActions = [quantitated]

        assert isinstance(trades, list)
        assert len(trades) == 1
        assert trades[0] == quantitated

    def test_capital_gain_lines_type_alias(self):
        """Test CapitalGainLines type alias works as list."""
        # CapitalGainLines is an alias for List[CapitalGainLine]
        company = get_company("AAPL")
        currency = get_currency("USD")

        line = CapitalGainLine(
            ticker=company,
            currency=currency,
            sell_date=[TradeDate(2024, 3, 28)],
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=[TradeDate(2023, 1, 15)],
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        lines: CapitalGainLines = [line]

        assert isinstance(lines, list)
        assert len(lines) == 1
        assert lines[0] == line

    def test_sorted_date_ranges_type_alias(self):
        """Test SortedDateRanges type alias works as list."""
        # SortedDateRanges is an alias for List[Tuple[str, TradeDate]]
        date1 = TradeDate(2024, 3, 28)
        date2 = TradeDate(2023, 1, 15)

        ranges: SortedDateRanges = [("2024-03", date1), ("2023-01", date2)]

        assert isinstance(ranges, list)
        assert len(ranges) == 2
        assert ranges[0] == ("2024-03", date1)
        assert ranges[1] == ("2023-01", date2)

    def test_trade_cycle_per_company_type_alias(self):
        """Test TradeCyclePerCompany type alias works as dictionary."""
        # TradeCyclePerCompany is an alias for Dict[CurrencyCompany, TradeCycle]
        company = get_company("AAPL")
        currency = get_currency("USD")

        from shares_reporting.domain.entities import CurrencyCompany
        currency_company = CurrencyCompany(currency, company)
        cycle = TradeCycle()

        cycles: TradeCyclePerCompany = {currency_company: cycle}

        assert isinstance(cycles, dict)
        assert len(cycles) == 1
        assert cycles[currency_company] == cycle

    def test_capital_gain_lines_per_company_type_alias(self):
        """Test CapitalGainLinesPerCompany type alias works as dictionary."""
        # CapitalGainLinesPerCompany is an alias for Dict[CurrencyCompany, CapitalGainLines]
        company = get_company("AAPL")
        currency = get_currency("USD")

        from shares_reporting.domain.entities import CurrencyCompany
        currency_company = CurrencyCompany(currency, company)

        line = CapitalGainLine(
            ticker=company,
            currency=currency,
            sell_date=[TradeDate(2024, 3, 28)],
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=[TradeDate(2023, 1, 15)],
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        lines: CapitalGainLinesPerCompany = {currency_company: [line]}

        assert isinstance(lines, dict)
        assert len(lines) == 1
        assert len(lines[currency_company]) == 1
        assert lines[currency_company][0] == line

    def test_day_partitioned_trades_type_alias(self):
        """Test DayPartitionedTrades type alias works as dictionary."""
        # DayPartitionedTrades is an alias for Dict[TradeDate, TradePartsWithinDay]
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_date = TradeDate(2024, 3, 28)

        trade_parts = TradePartsWithinDay(company, currency)

        partitioned: DayPartitionedTrades = {trade_date: trade_parts}

        assert isinstance(partitioned, dict)
        assert len(partitioned) == 1
        assert partitioned[trade_date] == trade_parts

    def test_partitioned_trades_by_type_type_alias(self):
        """Test PartitionedTradesByType type alias works as dictionary."""
        # PartitionedTradesByType is an alias for Dict[TradeType, DayPartitionedTrades]
        from shares_reporting.domain.value_objects import TradeType

        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_date = TradeDate(2024, 3, 28)
        trade_parts = TradePartsWithinDay(company, currency)

        partitioned: PartitionedTradesByType = {
            TradeType.BUY: {trade_date: trade_parts},
            TradeType.SELL: {}
        }

        assert isinstance(partitioned, dict)
        assert len(partitioned) == 2
        assert TradeType.BUY in partitioned
        assert TradeType.SELL in partitioned
        assert len(partitioned[TradeType.BUY]) == 1
        assert len(partitioned[TradeType.SELL]) == 0

    def test_currency_to_coordinate_type_alias(self):
        """Test CurrencyToCoordinate type alias works as dictionary."""
        # CurrencyToCoordinate is an alias for Dict[str, int]
        coordinates: CurrencyToCoordinate = {"USD": 1, "EUR": 2, "GBP": 3}

        assert isinstance(coordinates, dict)
        assert len(coordinates) == 3
        assert coordinates["USD"] == 1
        assert coordinates["EUR"] == 2
        assert coordinates["GBP"] == 3

    def test_currency_to_coordinates_type_alias(self):
        """Test CurrencyToCoordinates type alias works as list of tuples."""
        # CurrencyToCoordinates is an alias for List[Tuple[str, int]]
        coordinates: CurrencyToCoordinates = [("USD", 1), ("EUR", 2), ("GBP", 3)]

        assert isinstance(coordinates, list)
        assert len(coordinates) == 3
        assert coordinates[0] == ("USD", 1)
        assert coordinates[1] == ("EUR", 2)
        assert coordinates[2] == ("GBP", 3)


class TestCollectionBehavior:
    """Test that collections behave correctly with domain objects."""

    def test_nested_collection_operations(self):
        """Test nested collection operations work correctly."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        from shares_reporting.domain.entities import CurrencyCompany

        currency_company = CurrencyCompany(currency, company)

        # Create nested structure
        cycles: TradeCyclePerCompany = {currency_company: TradeCycle()}
        lines_per_company: CapitalGainLinesPerCompany = {currency_company: []}

        # Add trades to cycle
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        quantitated = QuantitatedTradeAction(Decimal("5"), trade)
        cycles[currency_company].get(TradeType.BUY).append(quantitated)

        # Create capital gain line and add to collection
        line = CapitalGainLine(
            ticker=company,
            currency=currency,
            sell_date=[TradeDate(2024, 3, 28)],
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=[TradeDate(2023, 1, 15)],
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )
        lines_per_company[currency_company].append(line)

        # Verify nested structure
        assert cycles[currency_company].has_bought() is True
        assert len(lines_per_company[currency_company]) == 1
        assert lines_per_company[currency_company][0].ticker == company

    def test_day_partitioned_trades_with_multiple_days(self):
        """Test DayPartitionedTrades with multiple days."""
        company = get_company("AAPL")
        currency = get_currency("USD")

        date1 = TradeDate(2024, 3, 28)
        date2 = TradeDate(2024, 3, 29)

        trade_parts1 = TradePartsWithinDay(company, currency)
        trade_parts2 = TradePartsWithinDay(company, currency)

        partitioned: DayPartitionedTrades = {
            date1: trade_parts1,
            date2: trade_parts2
        }

        assert len(partitioned) == 2
        assert date1 in partitioned
        assert date2 in partitioned
        assert partitioned[date1] == trade_parts1
        assert partitioned[date2] == trade_parts2

    def test_sorted_date_ranges_sorting(self):
        """Test SortedDateRanges works with date sorting."""
        date1 = TradeDate(2024, 1, 15)
        date2 = TradeDate(2024, 3, 28)
        date3 = TradeDate(2023, 12, 10)

        # Create unsorted list
        unsorted = [("2024-03", date2), ("2024-01", date1), ("2023-12", date3)]

        # Sort by TradeDate
        sorted_ranges: SortedDateRanges = sorted(unsorted, key=lambda x: x[1])

        assert len(sorted_ranges) == 3
        # Should be in chronological order: 2023-12, 2024-01, 2024-03
        assert sorted_ranges[0][1] == date3  # 2023-12-10
        assert sorted_ranges[1][1] == date1  # 2024-01-15
        assert sorted_ranges[2][1] == date2  # 2024-03-28

    def test_collection_immutability_preservation(self):
        """Test that collections preserve immutability of domain objects."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        quantitated = QuantitatedTradeAction(Decimal("5"), trade)

        trades: QuantitatedTradeActions = [quantitated]

        # The QuantitatedTradeAction should still be immutable
        with pytest.raises(AttributeError):
            trades[0].quantity = Decimal("10")  # Should fail as QuantitatedTradeAction is immutable

    def test_collection_type_checking(self):
        """Test that collections maintain correct types."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        from shares_reporting.domain.entities import CurrencyCompany

        currency_company = CurrencyCompany(currency, company)

        # These should all work without type errors
        cycles: TradeCyclePerCompany = {currency_company: TradeCycle()}
        assert isinstance(cycles, dict)
        assert isinstance(list(cycles.keys())[0], CurrencyCompany)
        assert isinstance(list(cycles.values())[0], TradeCycle)

        lines: CapitalGainLines = []
        assert isinstance(lines, list)

        partitioned: DayPartitionedTrades = {}
        assert isinstance(partitioned, dict)

    def test_collection_edge_cases(self):
        """Test collections with edge cases."""
        # Empty collections
        empty_trades: QuantitatedTradeActions = []
        empty_lines: CapitalGainLines = []
        empty_cycles: TradeCyclePerCompany = {}
        empty_partitioned: DayPartitionedTrades = {}

        assert len(empty_trades) == 0
        assert len(empty_lines) == 0
        assert len(empty_cycles) == 0
        assert len(empty_partitioned) == 0

        # Collections with single items
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        quantitated = QuantitatedTradeAction(Decimal("5"), trade)

        single_trade: QuantitatedTradeActions = [quantitated]
        assert len(single_trade) == 1
        assert single_trade[0] == quantitated

        # Single key-value pair
        from shares_reporting.domain.entities import CurrencyCompany
        currency_company = CurrencyCompany(currency, company)
        single_cycle: TradeCyclePerCompany = {currency_company: TradeCycle()}
        assert len(single_cycle) == 1
        assert isinstance(list(single_cycle.values())[0], TradeCycle)