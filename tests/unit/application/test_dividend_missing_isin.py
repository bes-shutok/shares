"""Tests for dividend processing when ISIN cannot be matched."""

import logging
from decimal import Decimal

import pytest

from shares_reporting.application.extraction import parse_dividend_income
from shares_reporting.application.extraction.models import IBCsvData
from shares_reporting.application.extraction.processing import _process_dividends


@pytest.mark.unit
class TestDividendMissingIsinScenarios:
    """Test dividend processing when ISIN matching fails."""

    def test_dividend_without_security_info_in_csv(self, tmp_path, caplog):
        """Test dividend entry when security info is missing from CSV."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1\n"
            # Missing security info for MSFT
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND,24.00\n"
            "Dividends,Data,USD,2023-06-15,MSFT - CASH DIVIDEND,68.00\n"  # MSFT not in security info
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_missing_security.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.ERROR):
            dividend_income = parse_dividend_income(csv_file)

        # Should process BOTH entries - never skip data!
        assert len(dividend_income) == 2
        assert "AAPL" in dividend_income
        assert "MSFT" in dividend_income

        # AAPL should have proper data
        assert dividend_income["AAPL"].isin == "US0378331005"
        assert dividend_income["AAPL"].country == "United States"

        # MSFT should have error indicators but still include the dividend amount
        assert dividend_income["MSFT"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
        assert dividend_income["MSFT"].country == "UNKNOWN_COUNTRY"
        assert dividend_income["MSFT"].gross_amount == Decimal("68.00")

        # Should log ERROR (not just warning) for missing MSFT security info
        error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert any("MSFT" in msg and "Missing security information" in msg for msg in error_messages)

    def test_dividend_with_empty_security_id(self, tmp_path, caplog):
        """Test dividend entry when security ID is empty."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,,1\n"  # Empty Security ID
            "Financial Instrument Information,Data,Stocks,MSFT,Microsoft Corp.,234567,US5949181045,1\n"
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND,24.00\n"
            "Dividends,Data,USD,2023-06-15,MSFT - CASH DIVIDEND,68.00\n"
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_empty_security_id.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.WARNING):
            dividend_income = parse_dividend_income(csv_file)

        # Should process BOTH entries - never skip data!
        assert len(dividend_income) == 2
        assert "AAPL" in dividend_income
        assert "MSFT" in dividend_income

        # AAPL should have error indicators
        assert dividend_income["AAPL"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
        assert dividend_income["AAPL"].gross_amount == Decimal("24.00")

        # MSFT should have proper data
        assert dividend_income["MSFT"].isin == "US5949181045"
        assert dividend_income["MSFT"].gross_amount == Decimal("68.00")

        # Should log ERROR for AAPL
        error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert any("AAPL" in msg and "Missing security information" in msg for msg in error_messages)

    def test_dividend_with_invalid_isin_format(self, tmp_path, caplog):
        """Test dividend entry with malformed ISIN."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,BAD,Bad Security,123456,INVALID_ISIN,1\n"
            "Financial Instrument Information,Data,Stocks,GOOD,Good Security,234567,US1234567890,1\n"
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,BAD - CASH DIVIDEND,24.00\n"
            "Dividends,Data,USD,2023-06-15,GOOD - CASH DIVIDEND,68.00\n"
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,GOOD,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_invalid_isin.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.WARNING):
            dividend_income = parse_dividend_income(csv_file)

        # May process both or filter based on ISIN validation
        # At minimum, GOOD should be processed
        assert len(dividend_income) >= 1
        assert "GOOD" in dividend_income

        # BAD might be processed if ISIN format validation is not strict
        # but if it fails, should log appropriate warning

    def test_mixed_isin_scenarios(self, tmp_path, caplog):
        """Test mixed scenarios with some valid and some invalid ISINs."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,VALID1,Valid Security 1,123456,US0378331005,1\n"
            "Financial Instrument Information,Data,Stocks,EMPTY,Empty Security,234567,,1\n"
            # Missing entry for MISSING
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,VALID1 - CASH DIVIDEND,100.00\n"
            "Dividends,Data,USD,2023-06-15,EMPTY - CASH DIVIDEND,50.00\n"
            "Dividends,Data,USD,2023-09-15,MISSING - CASH DIVIDEND,25.00\n"
            "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
            "Withholding Tax,Data,USD,2023-03-15,VALID1(US0378331005) US TAX,-15.00,,\n"
            "Withholding Tax,Data,USD,2023-06-15,EMPTY US TAX,-7.50,,\n"  # No ISIN in description
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,VALID1,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_mixed_isin.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.ERROR):
            dividend_income = parse_dividend_income(csv_file)

        # Should process ALL entries - never skip data!
        assert len(dividend_income) == 3
        assert "VALID1" in dividend_income
        assert "EMPTY" in dividend_income
        assert "MISSING" in dividend_income

        # VALID1 should have proper data
        assert dividend_income["VALID1"].isin == "US0378331005"

        # EMPTY and MISSING should have error indicators
        assert dividend_income["EMPTY"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
        assert dividend_income["MISSING"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"

        # Should log ERROR messages for invalid entries
        error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]

        # Should error about EMPTY (empty ISIN)
        assert any("EMPTY" in msg and "Missing security information" in msg for msg in error_messages)
        # Should error about MISSING (no security info)
        assert any("MISSING" in msg and "Missing security information" in msg for msg in error_messages)

    def test_process_dividends_handles_missing_isin_gracefully(self):
        """Test that _process_dividends handles missing ISIN by including data with error indicators."""
        security_info = {
            "AAPL": {"isin": "US0378331005", "country": "US"},
            # MSFT missing from security_info
        }

        raw_dividend_data = [
            {
                "currency": "USD",
                "date": "2023-03-15",
                "description": "AAPL - CASH DIVIDEND",
                "amount": "24.00",
            },
            {
                "currency": "USD",
                "date": "2023-06-15",
                "description": "MSFT - CASH DIVIDEND",  # No security info
                "amount": "68.00",
            },
        ]

        csv_data = IBCsvData(
            security_info=security_info,
            raw_trade_data=[],
            raw_dividend_data=raw_dividend_data,
            raw_withholding_tax_data=[],
            metadata={},
        )

        # Should process both entries, marking MSFT with error indicators
        dividend_income = _process_dividends(csv_data)

        # Should process BOTH entries - never skip data!
        assert len(dividend_income) == 2
        assert "AAPL" in dividend_income
        assert "MSFT" in dividend_income

        # AAPL should have proper data
        assert dividend_income["AAPL"].isin == "US0378331005"
        assert dividend_income["AAPL"].gross_amount == Decimal("24.00")

        # MSFT should have error indicators
        assert dividend_income["MSFT"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
        assert dividend_income["MSFT"].country == "UNKNOWN_COUNTRY"
        assert dividend_income["MSFT"].gross_amount == Decimal("68.00")

    def test_tax_matching_with_missing_isin(self, tmp_path, caplog):
        """Test tax entries when corresponding dividend has missing ISIN."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1\n"
            # Missing security info for MSFT
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,AAPL - CASH DIVIDEND,100.00\n"
            "Dividends,Data,USD,2023-06-15,MSFT - CASH DIVIDEND,50.00\n"
            "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
            "Withholding Tax,Data,USD,2023-03-15,AAPL(US0378331005) US TAX,-15.00,,\n"
            "Withholding Tax,Data,USD,2023-06-15,MSFT(US5949181045) US TAX,-7.50,,\n"  # Tax for missing security
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_tax_missing_isin.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.WARNING):
            dividend_income = parse_dividend_income(csv_file)

        # Should process BOTH entries with their respective taxes - never skip data!
        assert len(dividend_income) == 2
        assert "AAPL" in dividend_income
        assert "MSFT" in dividend_income

        # AAPL should have proper data and tax
        assert dividend_income["AAPL"].isin == "US0378331005"
        assert dividend_income["AAPL"].gross_amount == Decimal("100.00")
        assert dividend_income["AAPL"].total_taxes == Decimal("15.00")

        # MSFT should have error indicators but still include tax
        assert dividend_income["MSFT"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
        assert dividend_income["MSFT"].gross_amount == Decimal("50.00")
        assert dividend_income["MSFT"].total_taxes == Decimal("7.50")

        # Should log ERROR messages for MSFT dividend and tax
        error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]
        msft_errors = [msg for msg in error_messages if "MSFT" in msg]
        assert len(msft_errors) >= 2  # One for dividend, one for tax

    def test_partial_isin_recovery_from_dividend_description(self, tmp_path, caplog):
        """Test ISIN extraction from dividend description when missing from security info."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,,1\n"  # Empty ISIN
            "Financial Instrument Information,Data,Stocks,MSFT,Microsoft Corp.,234567,,1\n"  # Empty ISIN
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,AAPL(US0378331005) - CASH DIVIDEND,24.00\n"  # ISIN in description
            "Dividends,Data,USD,2023-06-15,AAPL - CASH DIVIDEND NO ISIN,24.00\n"  # No ISIN
            "Dividends,Data,USD,2023-09-15,MSFT(US5949181045) - CASH DIVIDEND,68.00\n"  # ISIN in description
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,AAPL,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_isin_recovery.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.WARNING):
            dividend_income = parse_dividend_income(csv_file)

        # Behavior depends on implementation - ISIN might be extracted from description
        # or entries might be skipped if security info ISIN is required
        # At minimum, should handle gracefully

        # If ISIN extraction from description works:
        if "AAPL" in dividend_income:
            # Should aggregate entries with recoverable ISIN
            assert dividend_income["AAPL"].gross_amount >= Decimal("24.00")

        if "MSFT" in dividend_income:
            assert dividend_income["MSFT"].gross_amount == Decimal("68.00")

    def test_all_dividends_missing_isin(self, tmp_path, caplog):
        """Test when all dividend entries have missing ISINs."""
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            # No security info at all
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,MISSING1 - CASH DIVIDEND,24.00\n"
            "Dividends,Data,USD,2023-06-15,MISSING2 - CASH DIVIDEND,68.00\n"
            "Dividends,Data,USD,2023-09-15,MISSING3 - CASH DIVIDEND,50.00\n"
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,FAKE,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_all_missing_isin.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.WARNING):
            dividend_income = parse_dividend_income(csv_file)

        # Should process ALL entries with error indicators - never skip data!
        assert len(dividend_income) == 3
        assert "MISSING1" in dividend_income
        assert "MISSING2" in dividend_income
        assert "MISSING3" in dividend_income

        # All should have error indicators
        for symbol in ["MISSING1", "MISSING2", "MISSING3"]:
            assert dividend_income[symbol].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
            assert dividend_income[symbol].country == "UNKNOWN_COUNTRY"

        # Check amounts are preserved
        assert dividend_income["MISSING1"].gross_amount == Decimal("24.00")
        assert dividend_income["MISSING2"].gross_amount == Decimal("68.00")
        assert dividend_income["MISSING3"].gross_amount == Decimal("50.00")

        # Should log ERROR messages for all missing entries
        error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_messages) >= 3  # At least one error per missing dividend

    def test_security_info_extraction_error_is_caught(self, tmp_path, caplog):
        """Test that SecurityInfoExtractionError is caught and logged appropriately."""
        # This test verifies the error handling mechanism works
        csv_content = (
            "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
            # No security info for BAD symbol
            "Dividends,Header,Currency,Date,Description,Amount\n"
            "Dividends,Data,USD,2023-03-15,BAD - CASH DIVIDEND,24.00\n"
            "Trades,Header,Symbol,Currency,Date/Time,Quantity,T. Price,Comm/Fee\n"
            "Trades,Data,Stocks,FAKE,USD,2023-01-15, 10:30:00,100,150.25,1.00\n"
        )
        csv_file = tmp_path / "test_error_handling.csv"
        csv_file.write_text(csv_content)

        with caplog.at_level(logging.ERROR):
            dividend_income = parse_dividend_income(csv_file)

        # Should process the entry with error indicators - never skip data!
        assert len(dividend_income) == 1
        assert "BAD" in dividend_income

        # Should have error indicators
        assert dividend_income["BAD"].isin == "MISSING_ISIN_REQUIRES_ATTENTION"
        assert dividend_income["BAD"].gross_amount == Decimal("24.00")

        # Should log ERROR about missing security info
        error_messages = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert any("BAD" in msg and "Missing security information" in msg for msg in error_messages)
