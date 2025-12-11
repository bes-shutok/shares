"""Tests for ISIN country resolution functionality."""

from shares_reporting.infrastructure.isin_country import (
    is_valid_isin_format,
    isin_to_country,
    isin_to_country_code,
)


class TestIsinToCountry:
    """Test ISIN to country conversion."""

    def test_isin_to_country_should_convert_us_isin(self):
        # Given
        us_isin = "US0378331005"  # Apple Inc.

        # When
        result = isin_to_country(us_isin)

        # Then
        assert result == "United States"

    def test_isin_to_country_should_convert_cayman_islands_isin(self):
        # Given
        cayman_isin = "KYG905191022"

        # When
        result = isin_to_country(cayman_isin)

        # Then
        assert result == "Cayman Islands"

    def test_isin_to_country_should_convert_german_isin(self):
        # Given
        german_isin = "DE0005557508"  # Allianz

        # When
        result = isin_to_country(german_isin)

        # Then
        assert result == "Germany"

    def test_isin_to_country_should_return_unknown_for_invalid_isin(self):
        # Given
        invalid_isin = "Unknown1234567890"

        # When
        result = isin_to_country(invalid_isin)

        # Then
        assert result == "Unknown"

    def test_isin_to_country_should_return_unknown_for_empty_string(self):
        # Given
        empty_isin = ""

        # When
        result = isin_to_country(empty_isin)

        # Then
        assert result == "Unknown"

    def test_isin_to_country_should_return_unknown_for_none(self):
        # Given
        none_isin = None

        # When
        result = isin_to_country(none_isin)

        # Then
        assert result == "Unknown"

    def test_isin_to_country_should_handle_lower_case_input(self):
        # Given
        lower_case_isin = "us0378331005"

        # When
        result = isin_to_country(lower_case_isin)

        # Then
        assert result == "United States"


class TestIsinToCountryCode:
    """Test ISIN to country code conversion."""

    def test_isin_to_country_code_should_extract_us_code(self):
        # Given
        us_isin = "US0378331005"

        # When
        result = isin_to_country_code(us_isin)

        # Then
        assert result == "US"

    def test_isin_to_country_code_should_extract_cayman_code(self):
        # Given
        cayman_isin = "KYG905191022"

        # When
        result = isin_to_country_code(cayman_isin)

        # Then
        assert result == "KY"

    def test_isin_to_country_code_should_return_unknown_for_invalid_isin(self):
        # Given
        invalid_isin = ""

        # When
        result = isin_to_country_code(invalid_isin)

        # Then
        assert result == "Unknown"

    def test_isin_to_country_code_should_handle_short_input(self):
        # Given
        short_isin = "U"

        # When
        result = isin_to_country_code(short_isin)

        # Then
        assert result == "Unknown"


class TestIsValidIsinFormat:
    """Test ISIN format validation."""

    def test_is_valid_isin_format_should_validate_correct_format(self):
        # Given
        valid_isin = "US0378331005"

        # When
        result = is_valid_isin_format(valid_isin)

        # Then
        assert result is True

    def test_is_valid_isin_format_should_reject_too_short(self):
        # Given
        short_isin = "US123456789"

        # When
        result = is_valid_isin_format(short_isin)

        # Then
        assert result is False

    def test_is_valid_isin_format_should_reject_too_long(self):
        # Given
        long_isin = "US037833100512"

        # When
        result = is_valid_isin_format(long_isin)

        # Then
        assert result is False

    def test_is_valid_isin_format_should_reject_non_letter_country_code(self):
        # Given
        invalid_isin = "120378331005"

        # When
        result = is_valid_isin_format(invalid_isin)

        # Then
        assert result is False

    def test_is_valid_isin_format_should_reject_non_digit_check_digit(self):
        # Given
        invalid_isin = "US037833100X"

        # When
        result = is_valid_isin_format(invalid_isin)

        # Then
        assert result is False

    def test_is_valid_isin_format_should_reject_empty_string(self):
        # Given
        empty_isin = ""

        # When
        result = is_valid_isin_format(empty_isin)

        # Then
        assert result is False

    def test_is_valid_isin_format_should_reject_none(self):
        # Given
        none_isin = None

        # When
        result = is_valid_isin_format(none_isin)

        # Then
        assert result is False
