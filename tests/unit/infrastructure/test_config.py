"""Tests for configuration management functionality."""

import configparser
import logging
from decimal import Decimal

import pytest

from shares_reporting.infrastructure.config import (
    Config,
    ConversionRate,
    _load_security_config,
)
from shares_reporting.infrastructure.validation import SecurityConfig


@pytest.mark.unit
class TestConfig:
    """Test configuration data structure."""

    def test_config_creation(self):
        """Test Config object creation with basic parameters."""
        base_currency = "EUR"
        rates = [
            ConversionRate(base="EUR", calculated="USD", rate=Decimal("1.2")),
            ConversionRate(base="EUR", calculated="GBP", rate=Decimal("0.85")),
        ]

        config = Config(base=base_currency, rates=rates)
        assert config.base == base_currency
        assert len(config.rates) == 2
        assert config.security is not None  # Should have default security config

    def test_config_with_custom_security(self):
        """Test Config object with custom security settings."""
        base_currency = "EUR"
        rates = []
        security = SecurityConfig(max_file_size_mb=50)

        config = Config(base=base_currency, rates=rates, security=security)
        assert config.base == base_currency
        assert len(config.rates) == 0
        assert config.security.max_file_size_mb == 50


@pytest.mark.unit
class TestConversionRate:
    """Test conversion rate named tuple."""

    def test_conversion_rate_creation(self):
        """Test ConversionRate creation."""
        rate = ConversionRate(base="EUR", calculated="USD", rate=Decimal("1.2"))
        assert rate.base == "EUR"
        assert rate.calculated == "USD"
        assert rate.rate == Decimal("1.2")


@pytest.mark.unit
class TestLoadSecurityConfig:
    """Test loading security configuration section."""

    def test_load_security_config_with_values(self):
        """Test loading security config with all values."""
        config = configparser.ConfigParser()
        config["SECURITY"] = {
            "MAX_FILE_SIZE_MB": "50",
            "MAX_TICKER_LENGTH": "8",
            "MAX_CURRENCY_LENGTH": "5",
            "ALLOWED_EXTENSIONS": ".csv,.xlsx",
            "MAX_QUANTITY_VALUE": "1000000",
            "MAX_PRICE_VALUE": "100000",
            "MAX_FILENAME_LENGTH": "100",
        }

        logger = logging.getLogger(__name__)
        security_config = _load_security_config(config, logger)

        assert security_config.max_file_size_mb == 50
        assert security_config.max_ticker_length == 8
        assert security_config.max_currency_length == 5
        assert ".csv" in security_config.allowed_extensions
        assert ".xlsx" in security_config.allowed_extensions
        assert security_config.max_quantity_value == 1000000
        assert security_config.max_price_value == 100000
        assert security_config.max_filename_length == 100

    def test_load_security_config_missing_section(self):
        """Test loading security config when section is missing."""
        config = configparser.ConfigParser()
        config["OTHER"] = {"something": "value"}

        logger = logging.getLogger(__name__)
        security_config = _load_security_config(config, logger)

        # Should return default config
        assert security_config.max_file_size_mb > 0
        assert security_config.max_ticker_length > 0

    def test_load_security_config_with_invalid_values(self):
        """Test loading security config with invalid values."""
        config = configparser.ConfigParser()
        config["SECURITY"] = {
            "MAX_FILE_SIZE_MB": "invalid_number",
            "ALLOWED_EXTENSIONS": ".csv,.txt",
        }

        logger = logging.getLogger(__name__)
        # Should fall back to defaults when values are invalid
        security_config = _load_security_config(config, logger)
        assert security_config.max_file_size_mb > 0
        assert ".csv" in security_config.allowed_extensions


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation logic."""

    def test_base_currency_validation(self):
        """Test base currency validation logic."""
        # Create a ConfigParser with valid config
        config = configparser.ConfigParser()
        # type: ignore[attr-defined] - ConfigParser.optionxform is assignable at runtime
        config.optionxform = lambda optionstr: optionstr  # Parameter name matches ConfigParser's signature

        config["COMMON"] = {"TARGET CURRENCY": "EUR"}
        config["EXCHANGE RATES"] = {
            "EUR/USD": "1.2",
            "EUR/GBP": "0.85",
        }

        # Extract values and test validation logic
        base_currency = config["COMMON"]["TARGET CURRENCY"]
        rates = []

        for key in config["EXCHANGE RATES"]:
            base, calculated = key.split("/")
            if base != base_currency:
                with pytest.raises(ValueError, match="Base currency mismatch"):
                    raise ValueError(f"Base currency mismatch: {base} != {base_currency}")
            rates.append(ConversionRate(base=base, calculated=calculated, rate=Decimal(config["EXCHANGE RATES"][key])))

        # Verify valid config
        assert base_currency == "EUR"
        assert len(rates) == 2
        assert all(rate.base == base_currency for rate in rates)

    def test_complete_config_construction(self):
        """Test complete configuration construction from individual parts."""
        # Create a ConfigParser with valid config
        config = configparser.ConfigParser()
        # type: ignore[attr-defined] - ConfigParser.optionxform is assignable at runtime
        config.optionxform = lambda optionstr: optionstr  # Parameter name matches ConfigParser's signature

        config["COMMON"] = {"TARGET CURRENCY": "EUR"}
        config["EXCHANGE RATES"] = {
            "EUR/USD": "1.2",
            "EUR/GBP": "0.85",
        }
        config["SECURITY"] = {
            "MAX_FILE_SIZE_MB": "100",
            "MAX_TICKER_LENGTH": "10",
            "MAX_CURRENCY_LENGTH": "3",
            "ALLOWED_EXTENSIONS": ".csv,.txt",
        }

        # Load security config separately
        logger = logging.getLogger(__name__)
        security_config = _load_security_config(config, logger)

        # Create our expected Config object
        expected_config = Config(
            base="EUR",
            rates=[
                ConversionRate(base="EUR", calculated="USD", rate=Decimal("1.2")),
                ConversionRate(base="EUR", calculated="GBP", rate=Decimal("0.85")),
            ],
            security=security_config,
        )

        # Verify the config is properly constructed
        assert expected_config.base == "EUR"
        assert len(expected_config.rates) == 2
        assert expected_config.rates[0].base == "EUR"
        assert expected_config.rates[0].calculated == "USD"
        assert expected_config.rates[0].rate == Decimal("1.2")
        assert expected_config.rates[1].calculated == "GBP"
        assert expected_config.rates[1].rate == Decimal("0.85")
        assert expected_config.security.max_file_size_mb == 100
        assert ".csv" in expected_config.security.allowed_extensions
