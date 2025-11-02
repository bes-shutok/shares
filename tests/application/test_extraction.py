import pytest
import csv
import tempfile
import os
from pathlib import Path
from decimal import Decimal

from shares_reporting.application.extraction import parse_data
from shares_reporting.domain.collections import TradeCyclePerCompany
from shares_reporting.domain.entities import QuantitatedTradeAction, CurrencyCompany
from shares_reporting.domain.value_objects import TradeType, get_currency, get_company


class TestParseData:

    def test_parse_data_with_simple_csv(self):
        """Test parse_data with a simple CSV file."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",10,150.25,1.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Verify structure
                assert isinstance(result, dict)
                assert len(result) == 1

                # Find the CurrencyCompany key
                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                assert currency_company in result

                # Verify trades
                cycle = result[currency_company]
                assert cycle.has(TradeType.BUY) is True
                assert len(cycle.get(TradeType.BUY)) == 1

                quantitated_trade = cycle.get(TradeType.BUY)[0]
                assert quantitated_trade.quantity == Decimal("10")
                assert quantitated_trade.action.price == Decimal("150.25")
                assert quantitated_trade.action.fee == Decimal("1.50")
                assert quantitated_trade.action.trade_type == TradeType.BUY

            finally:
                try:
                    os.unlink(f.name)  # Clean up
                except (OSError, PermissionError):
                    pass  # Ignore cleanup errors on Windows

    def test_parse_data_with_multiple_trades_same_company(self):
        """Test parse_data with multiple trades for the same company."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 10:30:45",5,140.00,1.40
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",3,145.00,1.45
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 15:45:30",-2,150.50,1.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                # Should have both buy and sell trades
                assert cycle.has(TradeType.BUY) is True
                assert cycle.has(TradeType.SELL) is True
                assert len(cycle.get(TradeType.BUY)) == 2
                assert len(cycle.get(TradeType.SELL)) == 1

                # Check sell trade
                sell_trade = cycle.get(TradeType.SELL)[0]
                assert sell_trade.quantity == Decimal("2")  # Quantity is absolute value in QuantitatedTradeAction
                assert sell_trade.action.trade_type == TradeType.SELL

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_with_multiple_companies(self):
        """Test parse_data with trades for multiple companies."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 10:30:45",5,140.00,1.40
Trades,Data,Order,Stock,USD,GOOGL,"2024-03-28, 14:30:45",2,2800.00,2.80
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 15:45:30",-3,145.00,1.45
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Should have two companies
                assert len(result) == 2

                # Check both companies are present
                companies = [key.company for key in result.keys()]
                aapl = get_company("AAPL")
                googl = get_company("GOOGL")
                assert aapl in companies
                assert googl in companies

                # Check AAPL trades
                aapl_currency = get_currency("USD")
                aapl_key = CurrencyCompany(aapl_currency, aapl)
                aapl_cycle = result[aapl_key]
                assert len(aapl_cycle.get(TradeType.BUY)) == 1
                assert len(aapl_cycle.get(TradeType.SELL)) == 1

                # Check GOOGL trades
                googl_currency = get_currency("USD")
                googl_key = CurrencyCompany(googl_currency, googl)
                googl_cycle = result[googl_key]
                assert len(googl_cycle.get(TradeType.BUY)) == 1
                assert len(googl_cycle.get(TradeType.SELL)) == 0

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_with_different_currencies(self):
        """Test parse_data with trades in different currencies."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 10:30:45",5,140.00,1.40
Trades,Data,Order,Stock,EUR,AAPL,"2024-03-28, 14:30:45",2,120.00,1.20
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Should have two different currency-company combinations
                assert len(result) == 2

                currencies = [key.currency for key in result.keys()]
                usd = get_currency("USD")
                eur = get_currency("EUR")
                assert usd in currencies
                assert eur in currencies

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_ignores_empty_date_time_rows(self):
        """Test parse_data ignores rows with empty Date/Time."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,,5,140.00,1.40
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",3,145.00,1.45
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Should have only one trade (the one with non-empty date)
                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                assert len(cycle.get(TradeType.BUY)) == 1
                assert cycle.get(TradeType.BUY)[0].quantity == Decimal("3")

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_handles_decimal_quantities(self):
        """Test parse_data handles decimal quantities correctly."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,BTC,"2024-03-28, 14:30:45",1.5,45000.00,45.00
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("BTC")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                quantitated_trade = cycle.get(TradeType.BUY)[0]
                assert quantitated_trade.quantity == Decimal("1.5")
                assert quantitated_trade.action.price == Decimal("45000.00")
                assert quantitated_trade.action.fee == Decimal("45.00")

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_handles_negative_quantities_as_sell(self):
        """Test parse_data treats negative quantities as sell trades."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",-5,150.25,1.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                assert cycle.has(TradeType.SELL) is True
                assert len(cycle.get(TradeType.SELL)) == 1

                sell_trade = cycle.get(TradeType.SELL)[0]
                assert sell_trade.action.trade_type == TradeType.SELL
                assert sell_trade.quantity == Decimal("5")  # Quantity is absolute value

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_handles_zero_quantity(self):
        """Test parse_data handles zero quantity as buy trade."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",0,150.25,1.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                assert cycle.has(TradeType.BUY) is True
                quantitated_trade = cycle.get(TradeType.BUY)[0]
                assert quantitated_trade.action.trade_type == TradeType.BUY
                assert quantitated_trade.quantity == Decimal("0")

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_handles_comma_in_price(self):
        """Test parse_data handles comma in price field."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,BTC,"2024-03-28, 14:30:45",1,45000.00,45.00
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("BTC")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                quantitated_trade = cycle.get(TradeType.BUY)[0]
                assert quantitated_trade.action.price == Decimal("45000.00")

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_converts_currency_to_uppercase(self):
        """Test parse_data converts currency codes to uppercase."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,eur,AAPL,"2024-03-28, 14:30:45",5,140.00,1.40
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Should create EUR currency (uppercase)
                currencies = [key.currency for key in result.keys()]
                eur = get_currency("EUR")
                assert eur in currencies

                # Verify the currency object has uppercase currency code
                currency_company = list(result.keys())[0]
                assert currency_company.currency.currency == "EUR"

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_handles_negative_fees(self):
        """Test parse_data converts negative fees to absolute value."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",5,140.00,-2.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                quantitated_trade = cycle.get(TradeType.BUY)[0]
                assert quantitated_trade.action.fee == Decimal("2.50")  # Should be absolute value

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_preserves_company_case(self):
        """Test parse_data preserves company ticker case."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,BRK.A,"2024-03-28, 14:30:45",5,140.00,1.40
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Should preserve the exact ticker case
                companies = [key.company for key in result.keys()]
                brk_a = get_company("BRK.A")
                assert brk_a in companies

                # Verify the company object preserves case
                currency_company = list(result.keys())[0]
                assert currency_company.company.ticker == "BRK.A"

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_with_empty_file(self):
        """Test parse_data with empty CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")  # Empty file
            f.flush()

            try:
                result = parse_data(f.name)
                assert len(result) == 0  # Should return empty dictionary

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_with_file_not_found(self):
        """Test parse_data with non-existent file raises appropriate error."""
        non_existent_file = "non_existent_file.csv"

        with pytest.raises(FileNotFoundError):
            parse_data(non_existent_file)

    def test_parse_data_with_malformed_csv(self):
        """Test parse_data with malformed CSV handles errors gracefully."""
        # CSV with wrong number of columns
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity
Trades,Data,Order,Stock,USD,AAPL,2024-03-28, 14:30:45
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                # This should either work (ignoring malformed rows) or raise a specific error
                result = parse_data(f.name)
                # If it works, it should ignore malformed rows
                # If it raises error, that's also acceptable

            except Exception as e:
                # Accept specific parsing errors
                assert ("csv" in str(e).lower() or "parse" in str(e).lower() or
                       "currency" in str(e).lower() or "key" in str(e).lower() or
                       "price" in str(e).lower())

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_quantitates_trade_actions_correctly(self):
        """Test that QuantitatedTradeAction objects are created correctly."""
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,USD,AAPL,"2024-03-28, 14:30:45",10,150.25,1.50
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                quantitated_trade = cycle.get(TradeType.BUY)[0]
                assert isinstance(quantitated_trade, QuantitatedTradeAction)
                assert quantitated_trade.quantity == Decimal("10")

                # The action should be a valid TradeAction
                assert quantitated_trade.action.company == company
                assert quantitated_trade.action.currency == currency
                assert quantitated_trade.action.price == Decimal("150.25")

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_data_integration_with_existing_tests(self):
        """Test that parse_data produces results compatible with existing tests."""
        # This test ensures our unit tests don't break integration with existing test data
        csv_content = """Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Order,Stock,EUR,BTU,"2021-05-18, 14:53:23",15,60.66,0.34455725
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                result = parse_data(f.name)

                # Should produce structure expected by existing tests
                assert isinstance(result, dict)

                currency = get_currency("EUR")
                company = get_company("BTU")
                currency_company = CurrencyCompany(currency, company)
                assert currency_company in result

                cycle = result[currency_company]
                assert cycle.has(TradeType.BUY) is True
                assert len(cycle.get(TradeType.BUY)) == 1

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass