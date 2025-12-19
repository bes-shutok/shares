"""Shared fixtures and configuration for pytest tests."""

from decimal import Decimal
from pathlib import Path

import pytest


def pytest_configure(config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")


@pytest.fixture
def sample_csv_content() -> str:
    """Provide a sample IB-style CSV content for testing."""
    return (
        "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
        "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1\n"
        "Financial Instrument Information,Data,Stocks,MSFT,Microsoft Corp.,234567,US5949181045,1\n"
        "Dividends,Header,Currency,Date,Description,Amount\n"
        "Dividends,Data,USD,2023-03-15,AAPL(US0378331005) CASH DIVIDEND 0.24 USD,24.00\n"
        "Dividends,Data,USD,2023-06-15,AAPL(US0378331005) CASH DIVIDEND 0.24 USD,24.00\n"
        "Dividends,Data,USD,2023-03-15,MSFT(US5949181045) CASH DIVIDEND 0.68 USD,68.00\n"
        "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
        "Withholding Tax,Data,USD,2023-03-15,AAPL(US0378331005) US TAX,-3.60,,\n"
        "Withholding Tax,Data,USD,2023-03-15,MSFT(US5949181045) US TAX,-10.20,,\n"
        "Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,"
        "Date/Time,Quantity,T. Price,Proceeds,Comm/Fee,Basis,Realized P/L,Code\n"
        'Trades,Data,Order,Stocks,USD,AAPL,"2023-01-15, 10:30:00",100,150.25,-15025.00,1.00,15026.00,0,O\n'
        'Trades,Data,Order,Stocks,USD,AAPL,"2023-12-15, 15:30:00",-100,160.50,16050.00,1.00,-16051.00,1000.00,C\n'
    )


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_csv_content: str) -> Path:
    """Create a temporary CSV file with sample content."""
    csv_file = tmp_path / "test_ib_export.csv"
    csv_file.write_text(sample_csv_content)
    return csv_file


@pytest.fixture
def malformed_csv_content() -> str:
    """Provide a malformed CSV content for error testing."""
    return (
        "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
        "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1\n"
        "Dividends,Header,Currency,Date,Description,Amount\n"
        "Dividends,Data,USD,invalid-date,AAPL - INVALID DATE,10.00\n"
        "Dividends,Data,,2023-06-15,AAPL - MISSING CURRENCY,15.00\n"
        "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
        "Withholding Tax,Data,USD,2023-03-15,INVALID SYMBOL US TAX,-5.00,,\n"
    )


@pytest.fixture
def csv_with_missing_isin() -> str:
    """CSV content with missing ISIN for testing error handling."""
    return (
        "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
        "Financial Instrument Information,Data,Stocks,MISSING,Missing ISIN Security,123456,,1\n"
        "Dividends,Header,Currency,Date,Description,Amount\n"
        "Dividends,Data,USD,2023-03-15,MISSING() CASH DIVIDEND,100.00\n"
        "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
        "Withholding Tax,Data,USD,2023-03-15,MISSING US TAX,-15.00,,\n"
        "Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,"
        "Date/Time,Quantity,T. Price,Proceeds,Comm/Fee,Basis,Realized P/L,Code\n"
        'Trades,Data,Order,Stocks,USD,MISSING,"2023-01-15, 10:30:00",10,100.00,-1000.00,1.00,1001.00,0,O\n'
        'Trades,Data,Order,Stocks,USD,MISSING,"2023-12-15, 15:30:00",-10,110.00,1100.00,1.00,-1101.00,100.00,C\n'
    )


@pytest.fixture
def multi_currency_csv_content() -> str:
    """CSV content with multiple currencies for testing currency conversion."""
    return (
        "Financial Instrument Information,Header,Asset Category,Symbol,Description,Conid,Security ID,Multiplier\n"
        "Financial Instrument Information,Data,Stocks,AAPL,Apple Inc.,123456,US0378331005,1\n"
        "Financial Instrument Information,Data,Stocks,ASML,ASML Holding N.V.,345678,NL0010273215,1\n"
        "Dividends,Header,Currency,Date,Description,Amount\n"
        "Dividends,Data,USD,2023-03-15,AAPL(US0378331005) CASH DIVIDEND USD,24.00\n"
        "Dividends,Data,EUR,2023-03-15,ASML(NL0010273215) CASH DIVIDEND EUR,22.00\n"
        "Withholding Tax,Header,Currency,Date,Description,Amount,Code\n"
        "Withholding Tax,Data,USD,2023-03-15,AAPL(US0378331005) US TAX,-3.60,,\n"
        "Withholding Tax,Data,EUR,2023-03-15,ASML(NL0010273215) TAX,-3.30,,\n"
        "Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,"
        "Date/Time,Quantity,T. Price,Proceeds,Comm/Fee,Basis,Realized P/L,Code\n"
        'Trades,Data,Order,Stocks,USD,AAPL,"2023-01-15, 10:30:00",10,150.00,-1500.00,1.00,1501.00,0,O\n'
        'Trades,Data,Order,Stocks,EUR,ASML,"2023-01-15, 10:30:00",10,400.00,-4000.00,1.00,4001.00,0,O\n'
    )


# Helper functions for tests
def create_csv_file(tmp_path: Path, content: str) -> Path:
    """Helper to create a CSV file with given content."""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(content)
    return csv_file


def assert_excel_file_exists_and_valid(report_path: Path) -> None:
    """Helper to verify Excel file was created and is valid."""
    assert report_path.exists(), f"Excel report not created at {report_path}"

    import openpyxl

    workbook = openpyxl.load_workbook(report_path)
    assert workbook.active is not None, "Workbook should have an active worksheet"
    workbook.close()


# Test data constants
SAMPLE_DIVIDEND_AMOUNT = Decimal("24.00")
SAMPLE_TAX_AMOUNT = Decimal("3.60")
SAMPLE_QUANTITY = 100
SAMPLE_PRICE = Decimal("150.25")
