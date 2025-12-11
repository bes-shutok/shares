from datetime import datetime

import pytest

from shares_reporting.domain.exceptions import DataValidationError
from shares_reporting.domain.value_objects import (
    Company,
    Currency,
    TradeDate,
    TradeType,
    parse_company,
    parse_currency,
    parse_trade_date,
)


class TestTradeDate:
    def test_trade_date_creation(self):
        """Test that TradeDate can be created with valid parameters."""
        trade_date = TradeDate(2024, 3, 28)
        assert trade_date.year == 2024
        assert trade_date.month == 3
        assert trade_date.day == 28

    def test_get_month_name_should_return_correct_month_name(self):
        """Test that get_month_name returns the correct month name."""
        trade_date = TradeDate(2024, 3, 28)
        assert trade_date.get_month_name() == "March"

    def test_get_month_name_with_december(self):
        """Test get_month_name with December."""
        trade_date = TradeDate(2024, 12, 25)
        assert trade_date.get_month_name() == "December"

    def test_get_month_name_with_january(self):
        """Test get_month_name with January."""
        trade_date = TradeDate(2024, 1, 1)
        assert trade_date.get_month_name() == "January"

    def test_repr_should_return_formatted_date_string(self):
        """Test that __repr__ returns properly formatted date string."""
        trade_date = TradeDate(2024, 3, 28)
        assert repr(trade_date) == "[28 March, 2024]"

    def test_repr_with_different_dates(self):
        """Test __repr__ with various dates."""
        dates_and_expected = [
            (TradeDate(2021, 1, 5), "[5 January, 2021]"),
            (TradeDate(2023, 12, 31), "[31 December, 2023]"),
            (TradeDate(2020, 2, 29), "[29 February, 2020]"),  # Leap year
        ]

        for trade_date, expected in dates_and_expected:
            assert repr(trade_date) == expected


class TestGetTradeDate:
    def test_get_trade_date_with_datetime_should_create_trade_date(self):
        """Test that get_trade_date creates TradeDate from datetime."""
        dt = datetime(2024, 3, 28, 14, 30, 45)
        trade_date = parse_trade_date(dt)

        assert trade_date.year == 2024
        assert trade_date.month == 3
        assert trade_date.day == 28

    def test_get_trade_date_with_different_datetime_values(self):
        """Test get_trade_date with various datetime values."""
        test_cases = [
            (datetime(2021, 1, 1, 0, 0, 0), TradeDate(2021, 1, 1)),
            (datetime(2023, 12, 31, 23, 59, 59), TradeDate(2023, 12, 31)),
            (datetime(2020, 2, 29, 12, 0, 0), TradeDate(2020, 2, 29)),  # Leap year
        ]

        for dt, expected in test_cases:
            result = parse_trade_date(dt)
            assert result == expected


class TestTradeType:
    def test_trade_type_enum_values(self):
        """Test that TradeType enum has correct values."""
        assert TradeType.BUY.value == 1
        assert TradeType.SELL.value == 2

    def test_trade_type_comparison(self):
        """Test TradeType comparison operations."""
        assert TradeType.BUY == TradeType.BUY
        assert TradeType.SELL == TradeType.SELL
        assert TradeType.BUY != TradeType.SELL

    def test_trade_type_string_representation(self):
        """Test TradeType string representation."""
        assert str(TradeType.BUY) == "TradeType.BUY"
        assert str(TradeType.SELL) == "TradeType.SELL"


class TestCurrency:
    def test_currency_creation(self):
        """Test that Currency can be created with valid currency code."""
        currency = Currency("USD")
        assert currency.currency == "USD"

    def test_currency_immutability(self):
        """Test that Currency is immutable (NamedTuple)."""
        currency = Currency("USD")
        with pytest.raises(AttributeError):
            currency.currency = "EUR"  # Should fail as NamedTuple is immutable


class TestGetCurrency:
    def test_get_currency_with_valid_three_letter_code_should_return_uppercase(self):
        """Test get_currency with valid 3-letter codes."""
        test_cases = [
            ("USD", "USD"),
            ("eur", "EUR"),  # Should be converted to uppercase
            ("GBP", "GBP"),
            ("JPY", "JPY"),
        ]

        for input_code, expected in test_cases:
            currency = parse_currency(input_code)
            assert currency.currency == expected

    def test_get_currency_with_mixed_case_should_convert_to_uppercase(self):
        """Test that get_currency converts mixed case to uppercase."""
        currency = parse_currency("UsD")
        assert currency.currency == "USD"

    def test_get_currency_with_lowercase_code_should_convert_to_uppercase(self):
        """Test get_currency with lowercase input."""
        currency = parse_currency("eur")
        assert currency.currency == "EUR"

    def test_get_currency_with_invalid_length_should_raise_value_error(self):
        """Test get_currency with invalid length raises ValueError."""
        invalid_codes = ["US", "USDD", "U", ""]

        for invalid_code in invalid_codes:
            with pytest.raises(DataValidationError, match="Currency is expected to be a length of 3"):
                parse_currency(invalid_code)

    def test_get_currency_with_empty_string_should_raise_value_error(self):
        """Test get_currency with empty string raises ValueError."""
        with pytest.raises(DataValidationError, match="Currency is expected to be a length of 3"):
            parse_currency("")

    def test_get_currency_with_invalid_characters_should_still_accept_if_length_3(self):
        """Test get_currency accepts 3-character codes even with special characters."""
        # The current validation only checks length, not character content
        codes_with_special_chars = ["US$", "EU@", "GB#"]

        for code in codes_with_special_chars:
            # These should pass validation as they are 3 characters
            currency = parse_currency(code)
            assert currency.currency == code.upper()

    def test_get_currency_with_4_character_code_should_raise_value_error(self):
        """Test get_currency with 4 characters raises ValueError."""
        with pytest.raises(DataValidationError, match="Currency is expected to be a length of 3"):
            parse_currency("USDD")


class TestCompany:
    def test_company_creation(self):
        """Test that Company can be created with valid ticker."""
        company = Company("AAPL")
        assert company.ticker == "AAPL"
        assert company.isin == ""
        assert company.country_of_issuance == "Unknown"

    def test_company_creation_with_isin_and_country(self):
        """Test that Company can be created with ISIN and country."""
        company = Company("AAPL", "US0378331005", "United States")
        assert company.ticker == "AAPL"
        assert company.isin == "US0378331005"
        assert company.country_of_issuance == "United States"

    def test_company_creation_with_empty_isin(self):
        """Test that Company can be created with empty ISIN."""
        company = Company("TSLA", "", "Unknown")
        assert company.ticker == "TSLA"
        assert company.isin == ""
        assert company.country_of_issuance == "Unknown"

    def test_company_immutability(self):
        """Test that Company is immutable (NamedTuple)."""
        company = Company("AAPL", "US0378331005", "United States")
        with pytest.raises(AttributeError):
            company.ticker = "GOOGL"  # Should fail as NamedTuple is immutable
        with pytest.raises(AttributeError):
            company.isin = "US02079K3059"  # Should fail as NamedTuple is immutable
        with pytest.raises(AttributeError):
            company.country_of_issuance = "Canada"  # Should fail as NamedTuple is immutable


class TestGetCompany:
    def test_get_company_with_valid_ticker_should_return_company(self):
        """Test get_company with valid ticker."""
        test_tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]

        for ticker in test_tickers:
            company = parse_company(ticker)
            assert company.ticker == ticker

    def test_get_company_with_mixed_case_should_preserve_case(self):
        """Test that get_company preserves case (case-sensitive)."""
        company = parse_company("aApL")
        assert company.ticker == "aApL"  # Should preserve exact case

    def test_get_company_with_whitespace_only_should_not_raise_value_error(self):
        """Test get_company with whitespace-only string does NOT raise ValueError (current behavior)."""
        # The current validation only checks length > 0, so whitespace passes
        whitespace_strings = ["   ", "\t", "\n", "  \t\n  "]

        for ws_string in whitespace_strings:
            # These should pass validation as they have length > 0
            company = parse_company(ws_string)
            assert company.ticker == ws_string  # Should preserve exact content

    def test_get_company_with_empty_string_should_raise_value_error(self):
        """Test get_company with truly empty string raises ValueError."""
        with pytest.raises(DataValidationError, match="Company is expected to be not empty"):
            parse_company("")

    def test_get_company_with_valid_characters(self):
        """Test get_company with various valid ticker characters."""
        valid_tickers = ["BRK.A", "BRK-B", "GOOGL", "MSFT", "^VIX", "USD=X"]

        for ticker in valid_tickers:
            company = parse_company(ticker)
            assert company.ticker == ticker

    def test_get_company_with_isin_and_country(self):
        """Test get_company with ISIN and country parameters."""
        company = parse_company("AAPL", "US0378331005", "United States")
        assert company.ticker == "AAPL"
        assert company.isin == "US0378331005"
        assert company.country_of_issuance == "United States"

    def test_get_company_with_only_isin(self):
        """Test get_company with ISIN but default country."""
        company = parse_company("TSLA", "US88160R1014")
        assert company.ticker == "TSLA"
        assert company.isin == "US88160R1014"
        assert company.country_of_issuance == "Unknown"  # Default value

    def test_get_company_with_custom_country(self):
        """Test get_company with custom country."""
        company = parse_company("RDS.A", "NL0000235190", "Netherlands")
        assert company.ticker == "RDS.A"
        assert company.isin == "NL0000235190"
        assert company.country_of_issuance == "Netherlands"

    def test_get_company_with_empty_isin_and_custom_country(self):
        """Test get_company with empty ISIN but custom country."""
        company = parse_company("UNKNOWN", "", "Canada")
        assert company.ticker == "UNKNOWN"
        assert company.isin == ""
        assert company.country_of_issuance == "Canada"

    def test_get_company_backwards_compatibility(self):
        """Test get_company with single parameter maintains backwards compatibility."""
        company = parse_company("MSFT")
        assert company.ticker == "MSFT"
        assert company.isin == ""  # Default
        assert company.country_of_issuance == "Unknown"  # Default
