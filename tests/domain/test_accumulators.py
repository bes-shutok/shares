import pytest

from shares_reporting.domain.exceptions import DataValidationError
from decimal import Decimal
from datetime import datetime

from shares_reporting.domain.accumulators import CapitalGainLineAccumulator, TradePartsWithinDay
from shares_reporting.domain.value_objects import TradeType, TradeDate, get_currency, get_company
from shares_reporting.domain.entities import TradeAction, QuantitatedTradeAction, CapitalGainLine


class TestCapitalGainLineAccumulator:
    def test_capital_gain_line_accumulator_creation(self):
        """Test CapitalGainLineAccumulator creation with valid parameters."""
        company = get_company("AAPL")
        currency = get_currency("USD")

        accumulator = CapitalGainLineAccumulator(company, currency)

        assert accumulator.company == company
        assert accumulator.currency == currency
        assert accumulator.sell_date is None
        assert accumulator.buy_date is None
        assert accumulator.sell_counts == []
        assert accumulator.buy_counts == []
        assert accumulator.sell_trades == []
        assert accumulator.buy_trades == []

    def test_add_trade_sell_should_set_sell_date_and_add_to_lists(self):
        """Test adding a sell trade sets sell date and adds to lists."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Create sell trade
        trade_date = "2024-03-28, 14:30:45"
        trade = TradeAction(company, trade_date, currency, "-5", "150.25", "1.50")

        accumulator.add_trade(Decimal("3"), trade)

        assert accumulator.sell_date == TradeDate(2024, 3, 28)
        assert accumulator.sell_counts == [Decimal("3")]
        assert len(accumulator.sell_trades) == 1
        assert accumulator.sell_trades[0] == trade
        assert accumulator.buy_date is None
        assert accumulator.buy_counts == []
        assert accumulator.buy_trades == []

    def test_add_trade_buy_should_set_buy_date_and_add_to_lists(self):
        """Test adding a buy trade sets buy date and adds to lists."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Create buy trade
        trade_date = "2023-01-15, 10:30:45"
        trade = TradeAction(company, trade_date, currency, "10", "140.00", "1.40")

        accumulator.add_trade(Decimal("5"), trade)

        assert accumulator.buy_date == TradeDate(2023, 1, 15)
        assert accumulator.buy_counts == [Decimal("5")]
        assert len(accumulator.buy_trades) == 1
        assert accumulator.buy_trades[0] == trade
        assert accumulator.sell_date is None
        assert accumulator.sell_counts == []
        assert accumulator.sell_trades == []

    def test_add_trade_multiple_sell_trades_same_date(self):
        """Test adding multiple sell trades on the same date."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Create multiple sell trades on the same date
        trade_date = "2024-03-28, 14:30:45"
        trade1 = TradeAction(company, trade_date, currency, "-5", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 15:30:45", currency, "-3", "151.00", "1.51")

        accumulator.add_trade(Decimal("3"), trade1)
        accumulator.add_trade(Decimal("2"), trade2)

        assert accumulator.sell_date == TradeDate(2024, 3, 28)
        assert accumulator.sell_counts == [Decimal("3"), Decimal("2")]
        assert len(accumulator.sell_trades) == 2
        assert accumulator.sell_trades[0] == trade1
        assert accumulator.sell_trades[1] == trade2

    def test_add_trade_multiple_buy_trades_same_date(self):
        """Test adding multiple buy trades on the same date."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Create multiple buy trades on the same date
        trade_date = "2023-01-15, 10:30:45"
        trade1 = TradeAction(company, trade_date, currency, "10", "140.00", "1.40")
        trade2 = TradeAction(company, "2023-01-15, 11:30:45", currency, "5", "142.00", "1.42")

        accumulator.add_trade(Decimal("5"), trade1)
        accumulator.add_trade(Decimal("3"), trade2)

        assert accumulator.buy_date == TradeDate(2023, 1, 15)
        assert accumulator.buy_counts == [Decimal("5"), Decimal("3")]
        assert len(accumulator.buy_trades) == 2
        assert accumulator.buy_trades[0] == trade1
        assert accumulator.buy_trades[1] == trade2

    def test_add_trade_sell_with_different_date_should_raise_error(self):
        """Test adding sell trade with different date raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add first sell trade
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        accumulator.add_trade(Decimal("3"), trade1)

        # Try to add sell trade with different date
        trade2 = TradeAction(company, "2024-03-29, 14:30:45", currency, "-3", "151.00", "1.51")

        with pytest.raises(
            DataValidationError,
            match="Incompatible dates in capital gain line add function! Expected",
        ):
            accumulator.add_trade(Decimal("2"), trade2)

    def test_add_trade_buy_with_different_date_should_raise_error(self):
        """Test adding buy trade with different date raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add first buy trade
        trade1 = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")
        accumulator.add_trade(Decimal("5"), trade1)

        # Try to add buy trade with different date
        trade2 = TradeAction(company, "2023-01-16, 10:30:45", currency, "5", "142.00", "1.42")

        with pytest.raises(
            DataValidationError,
            match="Incompatible dates in capital gain line add function! Expected",
        ):
            accumulator.add_trade(Decimal("3"), trade2)

    def test_sold_quantity_should_sum_sell_counts(self):
        """Test sold_quantity method sums sell counts."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add multiple sell trades
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        accumulator.add_trade(Decimal("3"), trade)
        accumulator.add_trade(Decimal("2"), trade)

        assert accumulator.sold_quantity() == Decimal("5")

    def test_sold_quantity_with_no_trades_should_return_zero(self):
        """Test sold_quantity with no trades returns zero."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        assert accumulator.sold_quantity() == Decimal("0")

    def test_bought_quantity_should_sum_buy_counts(self):
        """Test bought_quantity method sums buy counts."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add multiple buy trades
        trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")
        accumulator.add_trade(Decimal("4"), trade)
        accumulator.add_trade(Decimal("3"), trade)

        assert accumulator.bought_quantity() == Decimal("7")

    def test_bought_quantity_with_no_trades_should_return_zero(self):
        """Test bought_quantity with no trades returns zero."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        assert accumulator.bought_quantity() == Decimal("0")

    def test_finalize_should_reset_all_fields_and_return_capital_gain_line(self):
        """Test finalize resets all fields and returns CapitalGainLine."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add some trades
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")

        accumulator.add_trade(Decimal("3"), sell_trade)
        accumulator.add_trade(Decimal("3"), buy_trade)

        # Finalize
        capital_gain_line = accumulator.finalize()

        # Verify CapitalGainLine creation
        assert isinstance(capital_gain_line, CapitalGainLine)
        assert capital_gain_line.ticker == company
        assert capital_gain_line.currency == currency
        assert capital_gain_line.sell_date == TradeDate(2024, 3, 28)
        assert capital_gain_line.sell_quantities == [Decimal("3")]
        assert capital_gain_line.sell_trades == [sell_trade]
        assert capital_gain_line.buy_date == TradeDate(2023, 1, 15)
        assert capital_gain_line.buy_quantities == [Decimal("3")]
        assert capital_gain_line.buy_trades == [buy_trade]

        # Verify accumulator is reset
        assert accumulator.sell_date is None
        assert accumulator.buy_date is None
        assert accumulator.sell_counts == []
        assert accumulator.buy_counts == []
        assert accumulator.sell_trades == []
        assert accumulator.buy_trades == []

    def test_finalize_with_multiple_trades(self):
        """Test finalize with multiple trades."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add multiple trades
        sell_trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        sell_trade2 = TradeAction(company, "2024-03-28, 15:30:45", currency, "-3", "151.00", "1.51")
        buy_trade1 = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")
        buy_trade2 = TradeAction(company, "2023-01-15, 11:30:45", currency, "5", "142.00", "1.42")

        accumulator.add_trade(Decimal("3"), sell_trade1)
        accumulator.add_trade(Decimal("2"), sell_trade2)
        accumulator.add_trade(Decimal("4"), buy_trade1)
        accumulator.add_trade(Decimal("1"), buy_trade2)

        capital_gain_line = accumulator.finalize()

        assert capital_gain_line.sell_quantities == [Decimal("3"), Decimal("2")]
        assert capital_gain_line.buy_quantities == [Decimal("4"), Decimal("1")]
        assert len(capital_gain_line.sell_trades) == 2
        assert len(capital_gain_line.buy_trades) == 2

    def test_validate_with_empty_accumulator_should_raise_error(self):
        """Test validate with empty accumulator raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        with pytest.raises(DataValidationError, match="Cannot finalize empty Accumulator object!"):
            accumulator.finalize()  # finalize calls validate internally

    def test_validate_with_empty_sell_only_should_raise_error(self):
        """Test validate with only empty sell trades raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add buy trade but no sell trade
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")
        accumulator.add_trade(Decimal("5"), buy_trade)

        with pytest.raises(DataValidationError, match="Cannot finalize empty Accumulator object!"):
            accumulator.finalize()

    def test_validate_with_mismatched_quantities_should_raise_error(self):
        """Test validate with mismatched quantities raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add mismatched quantities
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")

        accumulator.add_trade(Decimal("6"), sell_trade)
        accumulator.add_trade(Decimal("5"), buy_trade)

        with pytest.raises(DataValidationError, match="Different counts for sales"):
            accumulator.finalize()

    def test_validate_with_mismatched_sell_counts_should_raise_error(self):
        """Test validate with mismatched sell counts raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add sell trades with different dates
        sell_trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        sell_trade2 = TradeAction(company, "2024-03-29, 14:30:45", currency, "-3", "151.00", "1.51")

        accumulator.add_trade(Decimal("3"), sell_trade1)

        with pytest.raises(
            DataValidationError,
            match="Incompatible dates in capital gain line add function! Expected",
        ):
            accumulator.add_trade(Decimal("2"), sell_trade2)

    def test_validate_with_mismatched_buy_counts_should_raise_error(self):
        """Test validate with mismatched buy counts raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        accumulator = CapitalGainLineAccumulator(company, currency)

        # Add buy trades with different dates
        buy_trade1 = TradeAction(company, "2023-01-15, 10:30:45", currency, "10", "140.00", "1.40")
        buy_trade2 = TradeAction(company, "2023-01-16, 10:30:45", currency, "5", "142.00", "1.42")

        accumulator.add_trade(Decimal("4"), buy_trade1)

        with pytest.raises(
            DataValidationError,
            match="Incompatible dates in capital gain line add function! Expected",
        ):
            accumulator.add_trade(Decimal("3"), buy_trade2)


class TestTradePartsWithinDay:
    def test_trade_parts_within_day_creation_with_parameters(self):
        """Test TradePartsWithinDay creation with all parameters."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_date = TradeDate(2024, 3, 28)
        dates = [datetime(2024, 3, 28, 14, 30, 45)]
        quantities = [Decimal("5")]
        trades = []  # Empty list for simplicity

        trade_parts = TradePartsWithinDay(
            company=company,
            currency=currency,
            trade_date=trade_date,
            trade_type=TradeType.BUY,
            dates=dates,
            quantities=quantities,
            trades=trades,
        )

        assert trade_parts.company == company
        assert trade_parts.currency == currency
        assert trade_parts.trade_date == trade_date
        assert trade_parts.trade_type == TradeType.BUY
        assert trade_parts.dates == dates
        assert trade_parts.quantities == quantities
        assert trade_parts.trades == trades

    def test_trade_parts_within_day_creation_without_parameters(self):
        """Test TradePartsWithinDay creation without parameters (default values)."""
        trade_parts = TradePartsWithinDay()

        assert trade_parts.company is None
        assert trade_parts.currency is None
        assert trade_parts.trade_type is None
        assert trade_parts.dates == []
        assert trade_parts.quantities == []
        assert trade_parts.trades == []

    def test_push_trade_part_first_trade_should_set_all_fields(self):
        """Test push_trade_part with first trade sets all fields."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()  # Don't pass company/currency to allow initialization

        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")

        trade_parts.push_trade_part(Decimal("5"), trade)

        assert trade_parts.company == company
        assert trade_parts.currency == currency
        assert trade_parts.trade_type == TradeType.BUY
        assert trade_parts.trade_date == TradeDate(2024, 3, 28)
        assert trade_parts.dates == [trade.date_time]
        assert trade_parts.quantities == [Decimal("5")]
        assert trade_parts.trades == [trade]

    def test_push_trade_part_first_sell_trade_should_set_sell_type(self):
        """Test push_trade_part with first sell trade sets SELL type."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Create sell trade
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")

        trade_parts.push_trade_part(Decimal("3"), trade)

        assert trade_parts.trade_type == TradeType.SELL

    def test_push_trade_part_compatible_trade_should_append_to_lists(self):
        """Test push_trade_part with compatible trade appends to lists."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add first trade
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade1)

        # Add compatible trade (same day, same type)
        trade2 = TradeAction(company, "2024-03-28, 15:30:45", currency, "8", "151.00", "1.51")
        trade_parts.push_trade_part(Decimal("3"), trade2)

        assert len(trade_parts.dates) == 2
        assert len(trade_parts.quantities) == 2
        assert len(trade_parts.trades) == 2
        assert trade_parts.dates == [trade1.date_time, trade2.date_time]
        assert trade_parts.quantities == [Decimal("5"), Decimal("3")]
        assert trade_parts.trades == [trade1, trade2]

    def test_push_trade_part_incompatible_trade_should_raise_error(self):
        """Test push_trade_part with incompatible trade raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add first trade (BUY)
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade1)

        # Try to add incompatible trade (different day)
        trade2 = TradeAction(company, "2024-03-29, 14:30:45", currency, "8", "151.00", "1.51")

        with pytest.raises(
            DataValidationError, match="Incompatible trade_type or date in DailyTradeLine! Expected"
        ):
            trade_parts.push_trade_part(Decimal("3"), trade2)

    def test_push_trade_part_incompatible_type_should_raise_error(self):
        """Test push_trade_part with incompatible trade type raises error."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add first trade (BUY)
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade1)

        # Try to add SELL trade to BUY collection
        trade2 = TradeAction(company, "2024-03-28, 15:30:45", currency, "-5", "151.00", "1.51")

        with pytest.raises(
            DataValidationError, match="Incompatible trade_type or date in DailyTradeLine! Expected"
        ):
            trade_parts.push_trade_part(Decimal("3"), trade2)

    def test_pop_trade_part_should_remove_and_return_earliest_trade(self):
        """Test pop_trade_part removes and returns earliest trade."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add multiple trades
        trade1 = TradeAction(company, "2024-03-28, 10:30:45", currency, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 11:30:45", currency, "8", "151.00", "1.51")
        trade3 = TradeAction(company, "2024-03-28, 14:30:45", currency, "5", "152.00", "1.52")

        trade_parts.push_trade_part(Decimal("5"), trade1)
        trade_parts.push_trade_part(Decimal("3"), trade2)
        trade_parts.push_trade_part(Decimal("2"), trade3)

        # Pop earliest trade (no parameters)
        popped = trade_parts.pop_trade_part()

        assert isinstance(popped, QuantitatedTradeAction)
        assert popped.quantity == Decimal("5")
        assert popped.action == trade1
        assert len(trade_parts.quantities) == 2
        assert trade_parts.quantities == [Decimal("3"), Decimal("2")]
        assert len(trade_parts.trades) == 2
        assert trade_parts.trades == [trade2, trade3]

    def test_pop_trade_part_removing_entire_trade(self):
        """Test pop_trade_part removing entire trade quantity."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        trade1 = TradeAction(company, "2024-03-28, 10:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade1)

        # Pop the entire trade (no parameters)
        popped = trade_parts.pop_trade_part()

        assert isinstance(popped, QuantitatedTradeAction)
        assert popped.quantity == Decimal("5")
        assert popped.action == trade1
        assert len(trade_parts.quantities) == 0  # Empty after removing the only trade
        assert len(trade_parts.trades) == 0

    def test_pop_trade_part_with_empty_trades_should_raise_error(self):
        """Test pop_trade_part with empty trades raises error."""
        trade_parts = TradePartsWithinDay()

        with pytest.raises(IndexError):
            trade_parts.pop_trade_part()

    def test_get_top_count_should_return_quantity_of_earliest_trade(self):
        """Test get_top_count returns quantity of earliest trade."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add trades
        trade1 = TradeAction(company, "2024-03-28, 10:30:45", currency, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 11:30:45", currency, "8", "151.00", "1.51")

        trade_parts.push_trade_part(Decimal("5"), trade1)
        trade_parts.push_trade_part(Decimal("3"), trade2)

        assert trade_parts.get_top_count() == Decimal("5")

    def test_get_top_count_with_empty_trades_should_raise_error(self):
        """Test get_top_count with empty trades raises error."""
        trade_parts = TradePartsWithinDay()

        with pytest.raises(IndexError):
            trade_parts.get_top_count()

    def test_get_top_index_should_find_earliest_date_index(self):
        """Test get_top_index finds earliest date index - this test accesses private method for testing purposes."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add trades in non-chronological order
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 10:30:45", currency, "8", "151.00", "1.51")
        trade3 = TradeAction(company, "2024-03-28, 12:30:45", currency, "5", "152.00", "1.52")

        trade_parts.push_trade_part(Decimal("5"), trade1)  # 14:30
        trade_parts.push_trade_part(Decimal("3"), trade2)  # 10:30
        trade_parts.push_trade_part(Decimal("2"), trade3)  # 12:30

        # Should find index 1 (the 10:30 trade)
        assert trade_parts._TradePartsWithinDay__get_top_index() == 1

    def test_earliest_date_should_return_sorted_earliest_date(self):
        """Test earliest_date returns the earliest date - this test accesses private method for testing purposes."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add trades in non-chronological order
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 10:30:45", currency, "8", "151.00", "1.51")

        trade_parts.push_trade_part(Decimal("5"), trade1)  # 14:30
        trade_parts.push_trade_part(Decimal("3"), trade2)  # 10:30

        assert trade_parts._TradePartsWithinDay__earliest_date() == trade2.date_time

    def test_is_not_empty_with_quantity_should_return_true(self):
        """Test is_not_empty with quantity returns True."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade)

        assert trade_parts.is_not_empty() is True

    def test_is_not_empty_with_zero_quantity_should_return_false(self):
        """Test is_not_empty with zero quantity returns False."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade)

        # Remove the trade to make it empty
        trade_parts.pop_trade_part()

        assert trade_parts.is_not_empty() is False

    def test_is_not_empty_with_empty_trades_should_return_false(self):
        """Test is_not_empty with empty trades returns False."""
        trade_parts = TradePartsWithinDay()

        assert trade_parts.is_not_empty() is False

    def test_quantity_should_sum_all_quantities(self):
        """Test quantity method sums all quantities."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        # Add multiple trades
        trade1 = TradeAction(company, "2024-03-28, 10:30:45", currency, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 11:30:45", currency, "8", "151.00", "1.51")

        trade_parts.push_trade_part(Decimal("5"), trade1)
        trade_parts.push_trade_part(Decimal("3"), trade2)

        assert trade_parts.quantity() == Decimal("8")

    def test_get_trades_should_return_trades_list(self):
        """Test get_trades returns trades list."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        trade_parts.push_trade_part(Decimal("5"), trade)

        assert trade_parts.get_trades() == [trade]

    def test_get_quantities_should_sum_quantities(self):
        """Test get_quantities sums quantities (same as quantity method)."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade_parts = TradePartsWithinDay()

        trade1 = TradeAction(company, "2024-03-28, 10:30:45", currency, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 11:30:45", currency, "8", "151.00", "1.51")

        trade_parts.push_trade_part(Decimal("5"), trade1)
        trade_parts.push_trade_part(Decimal("3"), trade2)

        assert trade_parts.get_quantities() == Decimal("8")

    def test_immutability_of_trades_list(self):
        """Test that trades list can be modified directly since dataclass is not frozen."""
        trade_parts = TradePartsWithinDay()

        # Direct assignment should work since dataclass is not frozen
        trade_parts.trades = []
        assert trade_parts.trades == []
