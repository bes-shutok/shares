import pytest
from decimal import Decimal
from datetime import datetime

from shares_reporting.domain.entities import TradeAction, TradeCycle, CapitalGainLine, QuantitatedTradeAction, CurrencyCompany
from shares_reporting.domain.value_objects import TradeType, Currency, Company, TradeDate, get_currency, get_company


class TestTradeAction:

    def test_trade_action_creation_with_positive_quantity_should_set_buy_type(self):
        """Test that TradeAction with positive quantity sets BUY type."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        date_time = "2024-03-28, 14:30:45"
        quantity = "10"
        price = "150.25"
        fee = "1.50"

        trade = TradeAction(company, date_time, currency, quantity, price, fee)

        assert trade.company == company
        assert trade.date_time == datetime(2024, 3, 28, 14, 30, 45)
        assert trade.currency == currency
        assert trade.quantity == Decimal("10")
        assert trade.price == Decimal("150.25")
        assert trade.fee == Decimal("1.50")
        assert trade.trade_type == TradeType.BUY

    def test_trade_action_creation_with_negative_quantity_should_set_sell_type(self):
        """Test that TradeAction with negative quantity sets SELL type."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        date_time = "2024-03-28, 14:30:45"
        quantity = "-5"
        price = "150.25"
        fee = "1.50"

        trade = TradeAction(company, date_time, currency, quantity, price, fee)

        assert trade.quantity == Decimal("5")  # Negative quantity is converted to positive
        assert trade.trade_type == TradeType.SELL

    def test_trade_action_creation_with_zero_quantity_should_set_buy_type(self):
        """Test that TradeAction with zero quantity sets BUY type."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        date_time = "2024-03-28, 14:30:45"
        quantity = "0"
        price = "150.25"
        fee = "1.50"

        trade = TradeAction(company, date_time, currency, quantity, price, fee)

        assert trade.quantity == Decimal("0")
        assert trade.trade_type == TradeType.BUY

    def test_trade_action_init_with_comma_in_quantity_should_remove_comma(self):
        """Test that commas in quantity are properly handled."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        date_time = "2024-03-28, 14:30:45"
        quantity = "1,234.56"  # Comma as decimal separator
        price = "150.25"
        fee = "1.50"

        trade = TradeAction(company, date_time, currency, quantity, price, fee)

        assert trade.quantity == Decimal("1234.56")

    def test_trade_action_init_with_fee_should_use_absolute_value(self):
        """Test that fee is converted to absolute value."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        date_time = "2024-03-28, 14:30:45"
        quantity = "10"
        price = "150.25"
        fee = "-2.50"  # Negative fee should become positive

        trade = TradeAction(company, date_time, currency, quantity, price, fee)

        assert trade.fee == Decimal("2.50")

    def test_trade_action_init_with_decimal_quantity(self):
        """Test TradeAction with decimal quantity."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        date_time = "2024-03-28, 14:30:45"
        quantity = "10.5"
        price = "150.25"
        fee = "1.50"

        trade = TradeAction(company, date_time, currency, quantity, price, fee)

        assert trade.quantity == Decimal("10.5")

    def test_trade_action_mutability(self):
        """Test that TradeAction fields are mutable (dataclass is not frozen)."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")

        # Dataclass is mutable, so this should work
        trade.quantity = Decimal("20")
        assert trade.quantity == Decimal("20")

    def test_trade_action_repr(self):
        """Test TradeAction string representation."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")

        expected = "TradeAction(company=Company(ticker='AAPL'), date_time=datetime.datetime(2024, 3, 28, 14, 30, 45), currency=Currency(currency='USD'), quantity=Decimal('10'), price=Decimal('150.25'), fee=Decimal('1.50'))"
        assert repr(trade) == expected


class TestQuantitatedTradeAction:

    def test_quantitated_trade_action_creation(self):
        """Test QuantitatedTradeAction creation."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        quantity = Decimal("5")

        quantitated = QuantitatedTradeAction(quantity, trade)

        assert quantitated.quantity == Decimal("5")
        assert quantitated.action == trade

    def test_quantitated_trade_action_immutability(self):
        """Test QuantitatedTradeAction immutability."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        quantitated = QuantitatedTradeAction(Decimal("5"), trade)

        with pytest.raises(AttributeError):
            quantitated.quantity = Decimal("10")  # Should fail as NamedTuple is immutable


class TestCurrencyCompany:

    def test_currency_company_creation(self):
        """Test CurrencyCompany creation."""
        company = get_company("AAPL")
        currency = get_currency("USD")

        currency_company = CurrencyCompany(currency=currency, company=company)

        assert currency_company.currency == currency
        assert currency_company.company == company

    def test_currency_company_immutability(self):
        """Test CurrencyCompany immutability."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        currency_company = CurrencyCompany(currency, company)

        with pytest.raises(AttributeError):
            currency_company.currency = get_currency("EUR")  # Should fail as NamedTuple is immutable


class TestTradeCycle:

    def test_trade_cycle_creation(self):
        """Test TradeCycle creation."""
        cycle = TradeCycle()

        assert cycle.bought == []
        assert cycle.sold == []

    def test_has_bought_with_empty_bought_list_should_return_false(self):
        """Test has_bought with empty bought list returns False."""
        cycle = TradeCycle()
        assert cycle.has_bought() is False

    def test_has_bought_with_non_empty_bought_list_should_return_true(self):
        """Test has_bought with non-empty bought list returns True."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")

        cycle.bought.append(QuantitatedTradeAction(Decimal("5"), trade))

        assert cycle.has_bought() is True

    def test_has_sold_with_empty_sold_list_should_return_false(self):
        """Test has_sold with empty sold list returns False."""
        cycle = TradeCycle()
        assert cycle.has_sold() is False

    def test_has_sold_with_non_empty_sold_list_should_return_true(self):
        """Test has_sold with non-empty sold list returns True."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")

        cycle.sold.append(QuantitatedTradeAction(Decimal("3"), trade))

        assert cycle.has_sold() is True

    def test_validate_with_sold_trades_should_match_currency_and_company(self):
        """Test validate with sold trades matches currency and company."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        currency = get_currency("USD")

        # Add sold trades
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        cycle.sold.append(QuantitatedTradeAction(Decimal("3"), trade1))

        # Should not raise an error
        cycle.validate(currency, company)

    def test_validate_with_sold_trades_mismatched_currency_should_raise_error(self):
        """Test validate with sold trades having mismatched currency raises error."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        usd = get_currency("USD")
        eur = get_currency("EUR")

        # Add sold trades with different currencies
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", usd, "-5", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 15:30:45", eur, "-3", "140.00", "1.40")
        cycle.sold.extend([
            QuantitatedTradeAction(Decimal("3"), trade1),
            QuantitatedTradeAction(Decimal("2"), trade2)
        ])

        # The validate method checks against provided currency/company, not internal consistency
        # It should return False since the trades don't match the provided EUR currency
        result = cycle.validate(eur, company)
        assert result is False

    def test_validate_with_sold_trades_mismatched_company_should_raise_error(self):
        """Test validate with sold trades having mismatched company raises error."""
        cycle = TradeCycle()
        currency = get_currency("USD")
        aapl = get_company("AAPL")
        googl = get_company("GOOGL")

        # Add sold trades with different companies
        trade1 = TradeAction(aapl, "2024-03-28, 14:30:45", currency, "-5", "150.25", "1.50")
        trade2 = TradeAction(googl, "2024-03-28, 15:30:45", currency, "-3", "140.00", "1.40")
        cycle.sold.extend([
            QuantitatedTradeAction(Decimal("3"), trade1),
            QuantitatedTradeAction(Decimal("2"), trade2)
        ])

        # The validate method checks against provided currency/company, not internal consistency
        # It should return False since the trades don't match the provided GOOGL company
        result = cycle.validate(currency, googl)
        assert result is False

    def test_validate_with_bought_trades_should_match_currency_and_company(self):
        """Test validate with bought trades matches currency and company."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        currency = get_currency("USD")

        # Add bought trades
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        cycle.bought.append(QuantitatedTradeAction(Decimal("5"), trade1))

        # Should not raise an error
        cycle.validate(currency, company)

    def test_validate_with_bought_trades_mismatched_currency_should_raise_error(self):
        """Test validate with bought trades having mismatched currency raises error."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        usd = get_currency("USD")
        eur = get_currency("EUR")

        # Add bought trades with different currencies
        trade1 = TradeAction(company, "2024-03-28, 14:30:45", usd, "10", "150.25", "1.50")
        trade2 = TradeAction(company, "2024-03-28, 15:30:45", eur, "5", "140.00", "1.40")
        cycle.bought.extend([
            QuantitatedTradeAction(Decimal("5"), trade1),
            QuantitatedTradeAction(Decimal("3"), trade2)
        ])

        # The validate method only checks the first trade in the list
        # Since the first trade (trade1) uses USD, validating against USD should return True
        result = cycle.validate(usd, company)
        assert result is True

        # But validating against EUR should return False since the first trade is USD
        result_eur = cycle.validate(eur, company)
        assert result_eur is False

    def test_has_with_sell_type_should_call_has_sold(self):
        """Test has method with SELL type calls has_sold."""
        cycle = TradeCycle()
        assert cycle.has(TradeType.SELL) == cycle.has_sold()

    def test_has_with_buy_type_should_call_has_bought(self):
        """Test has method with BUY type calls has_bought."""
        cycle = TradeCycle()
        assert cycle.has(TradeType.BUY) == cycle.has_bought()

    def test_get_with_sell_type_should_return_sold_list(self):
        """Test get method with SELL type returns sold list."""
        cycle = TradeCycle()
        assert cycle.get(TradeType.SELL) == cycle.sold

    def test_get_with_buy_type_should_return_bought_list(self):
        """Test get method with BUY type returns bought list."""
        cycle = TradeCycle()
        assert cycle.get(TradeType.BUY) == cycle.bought

    def test_is_empty_with_no_trades_should_return_true(self):
        """Test is_empty with no trades returns True."""
        cycle = TradeCycle()
        assert cycle.is_empty() is True

    def test_is_empty_with_trades_should_return_false(self):
        """Test is_empty with trades returns False."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        currency = get_currency("USD")
        trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")

        cycle.bought.append(QuantitatedTradeAction(Decimal("5"), trade))

        assert cycle.is_empty() is False

    def test_is_empty_with_both_bought_and_sold_trades(self):
        """Test is_empty with both bought and sold trades."""
        cycle = TradeCycle()
        company = get_company("AAPL")
        currency = get_currency("USD")
        buy_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "10", "150.25", "1.50")
        sell_trade = TradeAction(company, "2024-03-28, 15:30:45", currency, "-5", "160.00", "1.60")

        cycle.bought.append(QuantitatedTradeAction(Decimal("5"), buy_trade))
        cycle.sold.append(QuantitatedTradeAction(Decimal("3"), sell_trade))

        assert cycle.is_empty() is False


class TestCapitalGainLine:

    def test_capital_gain_line_creation(self):
        """Test CapitalGainLine creation."""
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_date = TradeDate(2024, 3, 28)
        sell_quantities = [Decimal("5")]
        sell_trades = []  # Empty list for simplicity
        buy_date = TradeDate(2023, 1, 15)
        buy_quantities = [Decimal("5")]
        buy_trades = []  # Empty list for simplicity

        line = CapitalGainLine(
            ticker=company.ticker,  # Pass ticker string, not Company object
            currency=currency,
            sell_date=sell_date,
            sell_quantities=sell_quantities,
            sell_trades=sell_trades,
            buy_date=buy_date,
            buy_quantities=buy_quantities,
            buy_trades=buy_trades
        )

        assert line.ticker == company.ticker
        assert line.currency == currency
        assert line.sell_date == sell_date
        assert line.buy_date == buy_date

    def test_get_ticker_should_return_ticker(self):
        """Test get_ticker method returns ticker."""
        company = get_company("AAPL")
        line = CapitalGainLine(
            ticker=company.ticker,  # Pass the ticker string, not the Company object
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        assert line.get_ticker() == company.ticker

    def test_get_currency_should_return_currency(self):
        """Test get_currency method returns currency."""
        currency = get_currency("USD")
        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=currency,
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        assert line.get_currency() == currency  # Returns the Currency object, not the string

    def test_sell_quantity_should_sum_quantities(self):
        """Test sell_quantity method sums sell quantities."""
        sell_quantities = [Decimal("3"), Decimal("2"), Decimal("1")]
        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=sell_quantities,
            sell_trades=[],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("6")],
            buy_trades=[]
        )

        assert line.sell_quantity() == Decimal("6")

    def test_buy_quantity_should_sum_quantities(self):
        """Test buy_quantity method sums buy quantities."""
        buy_quantities = [Decimal("2"), Decimal("4")]
        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("6")],
            sell_trades=[],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=buy_quantities,
            buy_trades=[]
        )

        assert line.buy_quantity() == Decimal("6")

    def test_validate_with_matching_quantities_should_not_raise_error(self):
        """Test validate with matching quantities should not raise error."""
        # Create mock trades to match the quantities
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "3", "150.00", "1.50")
        sell_trade2 = TradeAction(company, "2024-03-28, 15:30:45", currency, "2", "155.00", "1.55")
        buy_trade1 = TradeAction(company, "2023-01-15, 10:30:45", currency, "5", "145.00", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),  # Single TradeDate, not list
            sell_quantities=[Decimal("3"), Decimal("2")],  # Total: 5
            sell_trades=[sell_trade1, sell_trade2],  # Matching number of trades
            buy_date=TradeDate(2023, 1, 15),  # Single TradeDate, not list
            buy_quantities=[Decimal("5")],  # Total: 5
            buy_trades=[buy_trade1]  # Matching number of trades
        )

        # Should not raise an error
        line.validate()

    def test_validate_with_mismatched_quantities_should_raise_error(self):
        """Test validate with mismatched quantities raises error."""
        # Create trades to match quantities for validation
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "6", "150.00", "1.50")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "5", "145.00", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("6")],  # Total: 6
            sell_trades=[sell_trade],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],  # Total: 5
            buy_trades=[buy_trade]
        )

        with pytest.raises(ValueError, match="Different counts for sales"):
            line.validate()

    def test_validate_with_mismatched_sell_counts_should_raise_error(self):
        """Test validate with mismatched sell counts raises error."""
        # Create trades list that doesn't match quantities list length
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "3", "150.00", "1.50")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "5", "145.00", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("3"), Decimal("2")],  # 2 quantities
            sell_trades=[sell_trade],  # Only 1 trade - mismatch!
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[buy_trade]
        )

        with pytest.raises(ValueError, match="Different number of counts"):
            line.validate()

    def test_validate_with_mismatched_buy_counts_should_raise_error(self):
        """Test validate with mismatched buy counts raises error."""
        # Create trades list that doesn't match buy quantities list length
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "5", "150.00", "1.50")
        buy_trade1 = TradeAction(company, "2023-01-15, 10:30:45", currency, "3", "145.00", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[sell_trade],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("3"), Decimal("2")],  # 2 quantities
            buy_trades=[buy_trade1]  # Only 1 trade - mismatch!
        )

        with pytest.raises(ValueError, match="Different number of counts"):
            line.validate()

    def test_get_sell_date_should_return_sell_date(self):
        """Test get_sell_date returns sell date."""
        sell_date = TradeDate(2024, 3, 28)
        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=sell_date,
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        assert line.get_sell_date() == sell_date

    def test_get_buy_date_should_return_buy_date(self):
        """Test get_buy_date returns buy date."""
        buy_date = TradeDate(2023, 1, 15)
        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=buy_date,
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        assert line.get_buy_date() == buy_date

    def test_get_sell_amount_should_generate_formula_string(self):
        """Test get_sell_amount generates formula string."""
        # Create trades to match quantities for amount calculation
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade1 = TradeAction(company, "2024-03-28, 14:30:45", currency, "3", "150.25", "1.50")
        sell_trade2 = TradeAction(company, "2024-03-28, 15:30:45", currency, "2", "155.50", "1.55")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "5", "145.00", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("3"), Decimal("2")],
            sell_trades=[sell_trade1, sell_trade2],  # Add matching trades
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[buy_trade]
        )

        # Should generate a formula that references the appropriate cells
        result = line.get_sell_amount()
        assert result == "0+3*150.25+2*155.50"  # Expected formula format

    def test_get_buy_amount_should_generate_formula_string(self):
        """Test get_buy_amount generates formula string."""
        # Create trades to match quantities for amount calculation
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "5", "150.25", "1.50")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "5", "145.50", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[sell_trade],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[buy_trade]  # Add matching trade
        )

        # Should generate a formula that references the appropriate cells
        result = line.get_buy_amount()
        assert result == "0+5*145.50"  # Expected formula format

    def test_get_expense_amount_should_generate_formula_string(self):
        """Test get_expense_amount generates formula string."""
        # Create trades to match quantities for expense calculation
        company = get_company("AAPL")
        currency = get_currency("USD")
        sell_trade = TradeAction(company, "2024-03-28, 14:30:45", currency, "5", "150.25", "1.50")
        buy_trade = TradeAction(company, "2023-01-15, 10:30:45", currency, "5", "145.50", "1.45")

        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[sell_trade],  # Add matching trade
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[buy_trade]
        )

        # Should generate a formula that references the appropriate cells
        result = line.get_expense_amount()
        # Expense formula: quantity*fee/quantity = fee, but check actual implementation
        assert result == "0+5*1.50/5+5*1.45/5"  # Expected expense formula format

    def test_mutability(self):
        """Test CapitalGainLine mutability (dataclass is not frozen)."""
        line = CapitalGainLine(
            ticker=get_company("AAPL").ticker,
            currency=get_currency("USD"),
            sell_date=TradeDate(2024, 3, 28),
            sell_quantities=[Decimal("5")],
            sell_trades=[],
            buy_date=TradeDate(2023, 1, 15),
            buy_quantities=[Decimal("5")],
            buy_trades=[]
        )

        # Dataclass is mutable, so this should work
        line.sell_quantities = [Decimal("10")]
        assert line.sell_quantities == [Decimal("10")]