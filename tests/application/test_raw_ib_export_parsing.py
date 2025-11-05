"""
Tests for parse_raw_ib_export function that mirror the parse_data tests.

These tests duplicate the parse_data test scenarios but use the raw IB export format
with Financial Instrument Information and Trades sections.
"""

import pytest
import csv
import tempfile
import os
from pathlib import Path
from decimal import Decimal

from shares_reporting.application.extraction import parse_raw_ib_export
from shares_reporting.domain.collections import TradeCyclePerCompany
from shares_reporting.domain.entities import QuantitatedTradeAction, CurrencyCompany
from shares_reporting.domain.value_objects import TradeType, get_currency, get_company


class TestParseRawIbExport:
    """Test parse_raw_ib_export with various scenarios mirroring parse_data tests."""

    def test_parse_raw_ib_export_with_simple_csv(self):
        """Test parse_raw_ib_export with a simple raw IB export file."""
        # Given: Raw IB export format with Financial Instrument Information and Trades sections
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 14:30:45", "10", "150.25", "1.50"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                # When
                result = parse_raw_ib_export(f.name)

                # Then: Verify structure (same as parse_data test)
                assert isinstance(result, dict)
                assert len(result) == 1

                # Find the CurrencyCompany key
                currency = get_currency("USD")
                company = get_company("AAPL", "US0378331005", "United States")  # Enhanced with ISIN and country
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
                # Additional verification for raw IB export - ISIN and country data
                assert quantitated_trade.action.company.isin == "US0378331005"
                assert quantitated_trade.action.company.country_of_issuance == "United States"

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_raw_ib_export_with_multiple_trades_same_company(self):
        """Test parse_raw_ib_export with multiple trades for the same company."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 10:30:45", "5", "140.00", "1.40"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 14:30:45", "3", "145.00", "1.45"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 15:45:30", "-2", "150.50", "1.50"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL", "US0378331005", "United States")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                # Should have both buy and sell trades (same as parse_data test)
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

    def test_parse_raw_ib_export_with_multiple_companies(self):
        """Test parse_raw_ib_export with trades for multiple companies."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Financial Instrument Information", "Data", "Stocks", "GOOGL", "ALPHABET INC", "281398109", "US02079K3059", "GOOGL", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 10:30:45", "5", "140.00", "1.40"],
            ["Trades", "Data", "Order", "Stocks", "USD", "GOOGL", "2024-03-28, 14:30:45", "2", "2800.00", "2.80"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 15:45:30", "-3", "145.00", "1.45"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                # Should have 2 different currency-company pairs
                assert len(result) == 2

                # Check AAPL trades
                currency = get_currency("USD")
                aapl_company = get_company("AAPL", "US0378331005", "United States")
                aapl_currency_company = CurrencyCompany(currency, aapl_company)
                assert aapl_currency_company in result

                aapl_cycle = result[aapl_currency_company]
                assert aapl_cycle.has(TradeType.BUY) is True
                assert aapl_cycle.has(TradeType.SELL) is True

                # Check GOOGL trades
                googl_company = get_company("GOOGL", "US02079K3059", "United States")
                googl_currency_company = CurrencyCompany(currency, googl_company)
                assert googl_currency_company in result

                googl_cycle = result[googl_currency_company]
                assert googl_cycle.has(TradeType.BUY) is True
                assert googl_cycle.has(TradeType.SELL) is False

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_raw_ib_export_with_different_currencies(self):
        """Test parse_raw_ib_export with trades in different currencies."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Financial Instrument Information", "Data", "Stocks", "ASML", "ASML HOLDING NV", "33888791", "NL0010273215", "ASML", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 10:30:45", "5", "140.00", "1.40"],
            ["Trades", "Data", "Order", "Stocks", "EUR", "ASML", "2024-03-28, 14:30:45", "2", "450.50", "2.25"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                # Should have 2 different currency-company pairs
                assert len(result) == 2

                # Check USD-AAPL
                usd_currency = get_currency("USD")
                aapl_company = get_company("AAPL", "US0378331005", "United States")
                usd_aapl = CurrencyCompany(usd_currency, aapl_company)
                assert usd_aapl in result

                # Check EUR-ASML
                eur_currency = get_currency("EUR")
                asml_company = get_company("ASML", "NL0010273215", "Netherlands")
                eur_asml = CurrencyCompany(eur_currency, asml_company)
                assert eur_asml in result

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_raw_ib_export_ignores_empty_date_time_rows(self):
        """Test parse_raw_ib_export ignores rows with empty Date/Time."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 10:30:45", "5", "140.00", "1.40"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "", "3", "145.00", "1.45"],  # Empty date should be ignored
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 15:45:30", "-2", "150.50", "1.50"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL", "US0378331005", "United States")
                currency_company = CurrencyCompany(currency, company)
                cycle = result[currency_company]

                # Should only process 2 trades (ignoring the empty date row)
                assert len(cycle.get(TradeType.BUY)) == 1
                assert len(cycle.get(TradeType.SELL)) == 1

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_raw_ib_export_handles_missing_isin_data(self):
        """Test parse_raw_ib_export handles missing ISIN data gracefully."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            # No Financial Instrument Information data for TEST symbol
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "TEST", "2024-03-28, 10:30:45", "5", "140.00", "1.40"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                currency = get_currency("USD")
                company = get_company("TEST", "", "Unknown")  # Should default to empty ISIN and Unknown country
                currency_company = CurrencyCompany(currency, company)
                assert currency_company in result

                trade = result[currency_company].get(TradeType.BUY)[0]
                assert trade.action.company.isin == ""
                assert trade.action.company.country_of_issuance == "Unknown"

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_raw_ib_export_handles_decimal_quantities(self):
        """Test parse_raw_ib_export handles decimal quantities correctly."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 10:30:45", "2.5", "140.00", "1.40"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL", "US0378331005", "United States")
                currency_company = CurrencyCompany(currency, company)
                trade = result[currency_company].get(TradeType.BUY)[0]

                assert trade.quantity == Decimal("2.5")

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass

    def test_parse_raw_ib_export_handles_negative_quantities_as_sell(self):
        """Test parse_raw_ib_export treats negative quantities as sell trades."""
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-03-28, 10:30:45", "-5", "140.00", "1.40"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_content)
            f.flush()

            try:
                result = parse_raw_ib_export(f.name)

                currency = get_currency("USD")
                company = get_company("AAPL", "US0378331005", "United States")
                currency_company = CurrencyCompany(currency, company)
                trade = result[currency_company].get(TradeType.SELL)[0]

                assert trade.action.trade_type == TradeType.SELL
                assert trade.quantity == Decimal("5")  # Stored as absolute value

            finally:
                try:
                    os.unlink(f.name)
                except (OSError, PermissionError):
                    pass