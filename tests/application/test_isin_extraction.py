"""
Tests for ISIN extraction from raw IB exports.
"""

import pytest
from pathlib import Path
import tempfile
import csv

from shares_reporting.application.extraction import extract_isin_mapping, parse_raw_ib_export


class TestExtractIsinMapping:
    """Test ISIN mapping extraction from raw IB exports."""

    def test_extractIsinMappingShouldParseValidFinancialInstrumentSection(self):
        # Given
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Financial Instrument Information", "Data", "Stocks", "TSLA", "TESLA INC", "76792991", "US88160R1014", "TSLA", "NASDAQ", "1", "COMMON", ""],
            ["Financial Instrument Information", "Data", "Stocks", "1300", "TRIGIANT GROUP LTD", "104248119", "KYG905191022", "1300", "SEHK", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_content)
            temp_path = temp_file.name

        try:
            # When
            result = extract_isin_mapping(temp_path)

            # Then
            assert len(result) == 3
            assert result["AAPL"]["isin"] == "US0378331005"
            assert result["AAPL"]["country"] == "United States"
            assert result["TSLA"]["isin"] == "US88160R1014"
            assert result["TSLA"]["country"] == "United States"
            assert result["1300"]["isin"] == "KYG905191022"
            assert result["1300"]["country"] == "Cayman Islands"
        finally:
            Path(temp_path).unlink()

    def test_extractIsinMappingShouldHandleEmptyIsin(self):
        # Given
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", ""],  # Empty ISIN
            ["Financial Instrument Information", "Data", "Stocks", "TSLA", "TESLA INC", "76792991", "US88160R1014"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_content)
            temp_path = temp_file.name

        try:
            # When
            result = extract_isin_mapping(temp_path)

            # Then
            assert len(result) == 1
            assert "TSLA" in result
            assert "AAPL" not in result
            assert result["TSLA"]["isin"] == "US88160R1014"
        finally:
            Path(temp_path).unlink()

    def test_extractIsinMappingShouldHandleMissingFinancialInstrumentSection(self):
        # Given
        csv_content = [
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-01-01", "100", "150.00", "-1.00"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_content)
            temp_path = temp_file.name

        try:
            # When
            result = extract_isin_mapping(temp_path)

            # Then
            assert result == {}
        finally:
            Path(temp_path).unlink()


class TestParseRawIbExport:
    """Test raw IB export parsing."""

    def test_parseRawIbExportShouldProcessCompleteExport(self):
        # Given
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID", "Underlying", "Listing Exch", "Multiplier", "Type", "Code"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005", "AAPL", "NASDAQ", "1", "COMMON", ""],
            ["Financial Instrument Information", "Data", "Stocks", "TSLA", "TESLA INC", "76792991", "US88160R1014", "TSLA", "NASDAQ", "1", "COMMON", ""],
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "C. Price", "Proceeds", "Comm/Fee", "Basis", "Realized P/L", "MTM P/L", "Code"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-01-04, 09:58:29", "2", "181.33", "181.91", "-362.66", "-1", "363.66", "0", "1.16", "O"],
            ["Trades", "Data", "Order", "Stocks", "USD", "TSLA", "2024-03-06, 09:58:25", "3", "176.11", "176.54", "-528.33", "-1", "529.33", "0", "1.29", "O"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_content)
            temp_path = temp_file.name

        try:
            # When
            result = parse_raw_ib_export(temp_path)

            # Then
            assert len(result) == 2  # Two currency-company pairs

            # Check that companies have ISIN and country data
            for currency_company, trade_cycle in result.items():
                company = currency_company.company
                if company.ticker == "AAPL":
                    assert company.isin == "US0378331005"
                    assert company.country_of_issuance == "United States"
                elif company.ticker == "TSLA":
                    assert company.isin == "US88160R1014"
                    assert company.country_of_issuance == "United States"

                # Verify trades were processed
                assert trade_cycle.has_bought() or trade_cycle.has_sold()

        finally:
            Path(temp_path).unlink()

    def test_parseRawIbExportShouldHandleMissingTradesSection(self):
        # Given
        csv_content = [
            ["Financial Instrument Information", "Header", "Asset Category", "Symbol", "Description", "Conid", "Security ID"],
            ["Financial Instrument Information", "Data", "Stocks", "AAPL", "APPLE INC", "265598", "US0378331005"]
            # No Trades section
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_content)
            temp_path = temp_file.name

        try:
            # When / Then
            with pytest.raises(ValueError, match="No Trades section found"):
                parse_raw_ib_export(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parseRawIbExportShouldHandleMissingIsinData(self):
        # Given
        csv_content = [
            # No Financial Instrument Information section
            ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
            ["Trades", "Data", "Order", "Stocks", "USD", "AAPL", "2024-01-04, 09:58:29", "2", "181.33", "-1"]
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_content)
            temp_path = temp_file.name

        try:
            # When
            result = parse_raw_ib_export(temp_path)

            # Then
            assert len(result) == 1

            # Company should have default values when no ISIN data is available
            for currency_company, trade_cycle in result.items():
                company = currency_company.company
                assert company.ticker == "AAPL"
                assert company.isin == ""
                assert company.country_of_issuance == "Unknown"

        finally:
            Path(temp_path).unlink()