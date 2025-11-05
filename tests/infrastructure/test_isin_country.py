"""
Tests for ISIN country resolution functionality.
"""

import pytest

from shares_reporting.infrastructure.isin_country import (
    isin_to_country,
    isin_to_country_code,
    is_valid_isin_format
)


class TestIsinToCountry:
    """Test ISIN to country conversion."""

    def test_isinToCountryShouldConvertUsIsin(self):
        # Given
        us_isin = "US0378331005"  # Apple Inc.

        # When
        result = isin_to_country(us_isin)

        # Then
        assert result == "United States"

    def test_isinToCountryShouldConvertCaymanIslandsIsin(self):
        # Given
        cayman_isin = "KYG905191022"

        # When
        result = isin_to_country(cayman_isin)

        # Then
        assert result == "Cayman Islands"

    def test_isinToCountryShouldConvertGermanIsin(self):
        # Given
        german_isin = "DE0005557508"  # Allianz

        # When
        result = isin_to_country(german_isin)

        # Then
        assert result == "Germany"

    def test_isinToCountryShouldReturnUnknownForInvalidIsin(self):
        # Given
        invalid_isin = "XX1234567890"

        # When
        result = isin_to_country(invalid_isin)

        # Then
        assert result == "Unknown"

    def test_isinToCountryShouldReturnUnknownForEmptyString(self):
        # Given
        empty_isin = ""

        # When
        result = isin_to_country(empty_isin)

        # Then
        assert result == "Unknown"

    def test_isinToCountryShouldReturnUnknownForNone(self):
        # Given
        none_isin = None

        # When
        result = isin_to_country(none_isin)

        # Then
        assert result == "Unknown"

    def test_isinToCountryShouldHandleLowerCaseInput(self):
        # Given
        lower_case_isin = "us0378331005"

        # When
        result = isin_to_country(lower_case_isin)

        # Then
        assert result == "United States"


class TestIsinToCountryCode:
    """Test ISIN to country code conversion."""

    def test_isinToCountryCodeShouldExtractUsCode(self):
        # Given
        us_isin = "US0378331005"

        # When
        result = isin_to_country_code(us_isin)

        # Then
        assert result == "US"

    def test_isinToCountryCodeShouldExtractCaymanCode(self):
        # Given
        cayman_isin = "KYG905191022"

        # When
        result = isin_to_country_code(cayman_isin)

        # Then
        assert result == "KY"

    def test_isinToCountryCodeShouldReturnXXForInvalidIsin(self):
        # Given
        invalid_isin = ""

        # When
        result = isin_to_country_code(invalid_isin)

        # Then
        assert result == "XX"

    def test_isinToCountryCodeShouldHandleShortInput(self):
        # Given
        short_isin = "U"

        # When
        result = isin_to_country_code(short_isin)

        # Then
        assert result == "XX"


class TestIsValidIsinFormat:
    """Test ISIN format validation."""

    def test_isValidIsinFormatShouldValidateCorrectFormat(self):
        # Given
        valid_isin = "US0378331005"

        # When
        result = is_valid_isin_format(valid_isin)

        # Then
        assert result is True

    def test_isValidIsinFormatShouldRejectTooShort(self):
        # Given
        short_isin = "US123456789"

        # When
        result = is_valid_isin_format(short_isin)

        # Then
        assert result is False

    def test_isValidIsinFormatShouldRejectTooLong(self):
        # Given
        long_isin = "US037833100512"

        # When
        result = is_valid_isin_format(long_isin)

        # Then
        assert result is False

    def test_isValidIsinFormatShouldRejectNonLetterCountryCode(self):
        # Given
        invalid_isin = "120378331005"

        # When
        result = is_valid_isin_format(invalid_isin)

        # Then
        assert result is False

    def test_isValidIsinFormatShouldRejectNonDigitCheckDigit(self):
        # Given
        invalid_isin = "US037833100X"

        # When
        result = is_valid_isin_format(invalid_isin)

        # Then
        assert result is False

    def test_isValidIsinFormatShouldRejectEmptyString(self):
        # Given
        empty_isin = ""

        # When
        result = is_valid_isin_format(empty_isin)

        # Then
        assert result is False

    def test_isValidIsinFormatShouldRejectNone(self):
        # Given
        none_isin = None

        # When
        result = is_valid_isin_format(none_isin)

        # Then
        assert result is False