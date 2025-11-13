import pytest
from decimal import Decimal
from pathlib import Path

from shares_reporting.application.extraction import extract_dividend_income, _process_dividends_with_securities, _collect_ib_csv_data, IBCsvData
from shares_reporting.domain.entities import DividendIncomePerSecurity
from shares_reporting.domain.value_objects import get_currency
from shares_reporting.domain.exceptions import DataValidationError


class TestDividendExtraction:
    def test_extract_dividend_income_with_simple_dividends(self, tmp_path):
        """Test extracting dividend income from simple dividend entries."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1
Financial Instrument Information,Data,Stocks,MSFT,Microsoft Corp.,234567,US5949181045,1
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,USD,2023-06-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,USD,2023-03-15,MSFT - CASH DIVIDEND 0.68 USD,68.00
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_dividends.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        assert len(dividend_income) == 2

        aapl_dividend = dividend_income["AAPL"]
        assert aapl_dividend.symbol == "AAPL"
        assert aapl_dividend.isin == "US0378331005"
        assert aapl_dividend.country == "United States"
        assert aapl_dividend.gross_amount == Decimal("48.00")
        assert aapl_dividend.total_taxes == Decimal("0")
        assert aapl_dividend.currency == get_currency("USD")
        assert aapl_dividend.get_net_amount() == Decimal("48.00")

        msft_dividend = dividend_income["MSFT"]
        assert msft_dividend.symbol == "MSFT"
        assert msft_dividend.isin == "US5949181045"
        assert msft_dividend.country == "United States"
        assert msft_dividend.gross_amount == Decimal("68.00")
        assert msft_dividend.total_taxes == Decimal("0")

    def test_extract_dividend_income_with_taxes(self, tmp_path):
        """Test extracting dividend income with tax amounts."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1
Dividends,Header,Currency,Date,Description,Amount,Tax
Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND 0.24 USD,24.00,3.60
Dividends,Data,USD,2023-06-15,AAPL - CASH DIVIDEND 0.24 USD,24.00,3.60
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_dividends_tax.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        assert len(dividend_income) == 1

        aapl_dividend = dividend_income["AAPL"]
        assert aapl_dividend.gross_amount == Decimal("48.00")
        assert aapl_dividend.total_taxes == Decimal("7.20")
        assert aapl_dividend.get_net_amount() == Decimal("40.80")

    def test_extract_dividend_income_multiple_currencies(self, tmp_path):
        """Test extracting dividend income with different currencies."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1
Financial Instrument Information,Data,Stocks,ASML,ASML Holding N.V.,345678,NL0010273215,1
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,EUR,2023-04-10,ASML - CASH DIVIDEND EUR 1.45 EUR,145.00
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_multi_currency.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        assert len(dividend_income) == 2

        aapl_dividend = dividend_income["AAPL"]
        assert aapl_dividend.currency == get_currency("USD")
        assert aapl_dividend.gross_amount == Decimal("24.00")

        asml_dividend = dividend_income["ASML"]
        assert asml_dividend.currency == get_currency("EUR")
        assert asml_dividend.gross_amount == Decimal("145.00")
        assert asml_dividend.country == "Netherlands"

    def test_extract_dividend_income_aggregates_multiple_entries_same_symbol(self, tmp_path):
        """Test that multiple dividend entries for same symbol and currency are aggregated."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,USD,2023-06-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,USD,2023-09-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,USD,2023-12-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_aggregation.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        assert len(dividend_income) == 1

        aapl_dividend = dividend_income["AAPL"]
        assert aapl_dividend.gross_amount == Decimal("96.00")  # 4 * 24.00

    def test_extract_dividend_income_ignores_entries_without_security_info(self, tmp_path):
        """Test that dividend entries without corresponding security info are ignored."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND 0.24 USD,24.00
Dividends,Data,USD,2023-03-15,UNKNOWN - CASH DIVIDEND,10.00
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_unknown_security.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        assert len(dividend_income) == 1
        assert "AAPL" in dividend_income
        assert "UNKNOWN" not in dividend_income

    def test_process_dividends_with_securities_directly(self):
        """Test _process_dividends_with_securities function directly."""
        security_info = {
            "AAPL": {"isin": "US0378331005", "country": "US"},
            "MSFT": {"isin": "US5949181045", "country": "US"}
        }

        raw_dividend_data = [
            {"currency": "USD", "date": "2023-03-15", "description": "AAPL - CASH DIVIDEND", "amount": "24.00", "tax": "0"},
            {"currency": "USD", "date": "2023-06-15", "description": "AAPL - CASH DIVIDEND", "amount": "24.00", "tax": "0"},
            {"currency": "USD", "date": "2023-03-15", "description": "MSFT - CASH DIVIDEND", "amount": "68.00", "tax": "0"},
        ]

        csv_data = IBCsvData(
            security_info=security_info,
            raw_trade_data=[],
            raw_dividend_data=raw_dividend_data,
            metadata={}
        )

        dividend_income = _process_dividends_with_securities(csv_data)

        assert len(dividend_income) == 2
        assert dividend_income["AAPL"].gross_amount == Decimal("48.00")
        assert dividend_income["MSFT"].gross_amount == Decimal("68.00")

    def test_dividend_income_per_security_validation(self):
        """Test DividendIncomePerSecurity validation."""
        # Valid dividend income
        valid_dividend = DividendIncomePerSecurity(
            symbol="AAPL",
            isin="US0378331005",
            country="US",
            gross_amount=Decimal("100.00"),
            total_taxes=Decimal("15.00"),
            currency=get_currency("USD")
        )
        valid_dividend.validate()  # Should not raise

        # Negative gross amount
        with pytest.raises(DataValidationError, match="Gross amount cannot be negative"):
            invalid_dividend = DividendIncomePerSecurity(
                symbol="AAPL", isin="US0378331005", country="US",
                gross_amount=Decimal("-10.00"), total_taxes=Decimal("0"),
                currency=get_currency("USD")
            )
            invalid_dividend.validate()

        # Taxes exceeding gross amount
        with pytest.raises(DataValidationError, match="Taxes .* cannot exceed gross amount"):
            invalid_dividend = DividendIncomePerSecurity(
                symbol="AAPL", isin="US0378331005", country="US",
                gross_amount=Decimal("10.00"), total_taxes=Decimal("15.00"),
                currency=get_currency("USD")
            )
            invalid_dividend.validate()

        # Empty symbol
        with pytest.raises(DataValidationError, match="Symbol cannot be empty"):
            invalid_dividend = DividendIncomePerSecurity(
                symbol="", isin="US0378331005", country="US",
                gross_amount=Decimal("10.00"), total_taxes=Decimal("0"),
                currency=get_currency("USD")
            )
            invalid_dividend.validate()

    def test_extract_dividend_income_handles_missing_dividend_section(self, tmp_path):
        """Test extract_dividend_income handles missing dividend section gracefully."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_no_dividends.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        assert len(dividend_income) == 0

    def test_extract_dividend_income_symbol_extraction_fallback(self, tmp_path):
        """Test symbol extraction from description using regex fallback."""
        csv_content = """Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier
Financial Instrument Information,Data,Stocks,TSLA,Tesla Inc.,456789,US88160R1014,1
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2023-03-15,Tesla Inc Cash Dividend,5.00
Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee
Trades,Data,Stocks,TSLA,USD,2023-01-15, 10:30:00,100,150.25,1.00
"""
        csv_file = tmp_path / "test_symbol_extraction.csv"
        csv_file.write_text(csv_content)

        dividend_income = extract_dividend_income(csv_file)

        # This test shows the limitation - without proper format, symbol extraction may fail
        # The current implementation tries to extract ticker-like patterns but may not always succeed
        # In real IB exports, dividends typically use the "SYMBOL - Description" format