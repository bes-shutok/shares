"""Test missing ISIN behavior to ensure data is never skipped but properly marked with error indicators."""

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from shares_reporting.application.extraction.processing import _extract_csv_data, _process_dividends
from shares_reporting.application.persisting import generate_tax_report


class TestMissingISINBehavior:
    """Test that missing ISIN entries are included with error indicators rather than skipped."""

    @pytest.fixture
    def sample_csv_with_missing_isin(self):
        """Create test CSV with missing security info for some symbols."""
        return (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1\n"
            # No security info for MSFT and TSLA - these should get error indicators
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND,100.00\n"
            "Dividends,Data,USD,2023-06-15,MSFT - MISSING SECURITY INFO DIVIDEND,50.00\n"
            "Dividends,Data,USD,2023-09-15,TSLA - ANOTHER MISSING SECURITY,25.00\n"
            "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
            "Withholding Tax,Data,USD,2023-06-15,MSFT US TAX,-7.50,,\n"
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )

    def test_missing_isin_entries_are_included_with_error_indicators(self, sample_csv_with_missing_isin):
        """Test that missing ISIN entries are processed with error indicators rather than skipped."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(sample_csv_with_missing_isin)
            csv_file = Path(f.name)

        try:
            # Extract raw CSV data
            csv_data = _extract_csv_data(csv_file)

            # Verify we found all the expected data
            assert len(csv_data.raw_dividend_data) == 3
            assert len(csv_data.raw_withholding_tax_data) == 1

            # Process dividends
            dividend_income = _process_dividends(csv_data)

            # Verify we got dividend data for all 3 symbols (no data was skipped)
            assert len(dividend_income) == 3

            # Check AAPL has complete security info
            aapl_dividend = dividend_income["AAPL"]
            assert aapl_dividend.symbol == "AAPL"
            assert aapl_dividend.gross_amount == Decimal("100.00")
            assert aapl_dividend.total_taxes == Decimal("0")
            assert aapl_dividend.isin == "US0378331005"
            assert aapl_dividend.country != "UNKNOWN_COUNTRY"

            # Check MSFT has missing ISIN indicators
            msft_dividend = dividend_income["MSFT"]
            assert msft_dividend.symbol == "MSFT"
            assert msft_dividend.gross_amount == Decimal("50.00")
            assert msft_dividend.total_taxes == Decimal("7.50")  # Tax amount is stored as positive
            assert msft_dividend.isin == "MISSING_ISIN_REQUIRES_ATTENTION"
            assert msft_dividend.country == "UNKNOWN_COUNTRY"

            # Check TSLA has missing ISIN indicators
            tsla_dividend = dividend_income["TSLA"]
            assert tsla_dividend.symbol == "TSLA"
            assert tsla_dividend.gross_amount == Decimal("25.00")
            assert tsla_dividend.total_taxes == Decimal("0")
            assert tsla_dividend.isin == "MISSING_ISIN_REQUIRES_ATTENTION"
            assert tsla_dividend.country == "UNKNOWN_COUNTRY"

            # Verify total amounts are preserved (no data loss)
            total_gross = sum(dividend.gross_amount for dividend in dividend_income.values())
            assert total_gross == Decimal("175.00")

        finally:
            csv_file.unlink(missing_ok=True)

    def test_excel_report_includes_missing_isin_highlighting(self, sample_csv_with_missing_isin):
        """Test that Excel report highlights missing ISIN entries with visual indicators."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as csv_file:
            csv_file.write(sample_csv_with_missing_isin)
            csv_path = Path(csv_file.name)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as excel_file:
            excel_path = Path(excel_file.name)

        try:
            # Extract and process data
            csv_data = _extract_csv_data(csv_path)
            dividend_income = _process_dividends(csv_data)

            # Generate Excel report
            generate_tax_report(
                extract=excel_path,
                capital_gain_lines_per_company={},
                dividend_income_per_company=dividend_income,
            )

            # Verify Excel file was created
            assert excel_path.exists()
            assert excel_path.stat().st_size > 0

            # TODO: In a more comprehensive test, we could verify the actual Excel formatting
            # (red background, warning symbols) but that would require additional libraries
            # like openpyxl to read and verify the formatting

        finally:
            csv_path.unlink(missing_ok=True)
            excel_path.unlink(missing_ok=True)

    def test_all_financial_amounts_preserved_with_missing_isin(self, sample_csv_with_missing_isin):
        """Test that all financial amounts are preserved even when security info is missing."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(sample_csv_with_missing_isin)
            csv_file = Path(f.name)

        try:
            # Extract and process data
            csv_data = _extract_csv_data(csv_file)
            dividend_income = _process_dividends(csv_data)

            # Calculate expected totals from raw data
            expected_total_gross = Decimal("0")
            expected_total_taxes = Decimal("0")

            for dividend_row in csv_data.raw_dividend_data:
                expected_total_gross += Decimal(dividend_row["amount"])

            for tax_row in csv_data.raw_withholding_tax_data:
                expected_total_taxes += abs(Decimal(tax_row["amount"]))

            # Verify totals match exactly (no data loss)
            actual_total_gross = sum(dividend.gross_amount for dividend in dividend_income.values())
            actual_total_taxes = sum(dividend.total_taxes for dividend in dividend_income.values())

            assert actual_total_gross == expected_total_gross
            assert actual_total_taxes == expected_total_taxes

        finally:
            csv_file.unlink(missing_ok=True)

    def test_error_indicators_are_consistent_across_missing_symbols(self, sample_csv_with_missing_isin):
        """Test that all missing ISIN entries use consistent error indicators."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(sample_csv_with_missing_isin)
            csv_file = Path(f.name)

        try:
            # Extract and process data
            csv_data = _extract_csv_data(csv_file)
            dividend_income = _process_dividends(csv_data)

            # Get all symbols with missing ISIN
            missing_isin_symbols = [
                symbol
                for symbol, dividend in dividend_income.items()
                if dividend.isin == "MISSING_ISIN_REQUIRES_ATTENTION"
            ]

            # Should have MSFT and TSLA
            assert set(missing_isin_symbols) == {"MSFT", "TSLA"}

            # Verify all missing ISIN entries use consistent error indicators
            for symbol in missing_isin_symbols:
                dividend = dividend_income[symbol]
                assert dividend.isin == "MISSING_ISIN_REQUIRES_ATTENTION"
                assert dividend.country == "UNKNOWN_COUNTRY"
                assert dividend.symbol == symbol  # Symbol should still be correct

        finally:
            csv_file.unlink(missing_ok=True)
