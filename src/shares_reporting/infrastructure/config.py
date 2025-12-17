"""Configuration management for the shares reporting application."""

from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import NamedTuple

from .logging_config import create_module_logger
from .validation import DEFAULT_SECURITY_CONFIG, SecurityConfig


class ConversionRate(NamedTuple):
    """Represents a currency exchange rate pair.

    Attributes:
        base: The base currency code (e.g., 'EUR').
        calculated: The target currency code (e.g., 'USD').
    """

    base: str
    calculated: str
    rate: Decimal


@dataclass
class Config:
    """Application configuration container.

    Attributes:
        base: The base currency for reporting (e.g. 'EUR').
        rates: List of configured currency conversion pairs.
        security: Security configuration settings.
    """

    base: str
    rates: list[ConversionRate]
    security: SecurityConfig = field(default_factory=lambda: DEFAULT_SECURITY_CONFIG)


def load_configuration_from_file() -> Config:
    """Load configuration from the standard config.ini file.

    Returns:
        Config: The loaded application configuration.

    Raises:
        ValueError: If main currency or required exchange rates are missing.
    """
    logger = create_module_logger(__name__)
    config = configparser.ConfigParser()
    # Preserve case for option names
    # optionxform is a callable that transforms option names
    # Setting it to str preserves case sensitivity
    # Note: parameter name must be 'optionstr' to match ConfigParser's type annotation
    config.optionxform = lambda optionstr: optionstr

    config_path = "config.ini"
    try:
        files_read = config.read(config_path)
        if not files_read:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        logger.info("Loaded configuration from %s", config_path)
        logger.debug("Available sections: %s", list(config.sections()))

    except (configparser.Error, OSError) as e:
        logger.error("Failed to read configuration file %s: %s", config_path, e)
        raise

    try:
        target: str = config["COMMON"]["TARGET CURRENCY"]
        logger.debug("Target currency: %s", target)

        rates: list[ConversionRate] = []
        for key in config["EXCHANGE RATES"]:
            base, calculated = key.split("/")
            if base != target:
                raise ValueError(f"Base currency mismatch: {base} != {target}")
            rate_value = Decimal(config["EXCHANGE RATES"][key])
            rates.append(ConversionRate(base=base, calculated=calculated, rate=rate_value))
            logger.debug("Loaded exchange rate %s = %s", key, rate_value)

        logger.info("Loaded %d exchange rates for base currency %s", len(rates), target)

        # Load security settings
        security_config = _load_security_config(config, logger)

        return Config(base=target, rates=rates, security=security_config)

    except (KeyError, ValueError, AssertionError) as e:
        logger.error("Configuration parsing error: %s", e)
        raise


def _load_security_config(config: configparser.ConfigParser, logger: logging.Logger) -> SecurityConfig:
    """Load security configuration from config file or use defaults."""
    try:
        security_section = config["SECURITY"]

        # Parse security settings with fallback to defaults
        max_file_size_mb = int(security_section.get("MAX_FILE_SIZE_MB", "100"))
        max_ticker_length = int(security_section.get("MAX_TICKER_LENGTH", "10"))
        max_currency_length = int(security_section.get("MAX_CURRENCY_LENGTH", "3"))
        max_quantity_value = int(security_section.get("MAX_QUANTITY_VALUE", "10000000000"))
        max_price_value = int(security_section.get("MAX_PRICE_VALUE", "1000000000"))
        max_filename_length = int(security_section.get("MAX_FILENAME_LENGTH", "255"))

        # Parse allowed extensions
        extensions_str = security_section.get("ALLOWED_EXTENSIONS", ".csv,.txt")
        allowed_extensions = [ext.strip() for ext in extensions_str.split(",")]

        security_config = SecurityConfig(
            max_file_size_mb=max_file_size_mb,
            max_ticker_length=max_ticker_length,
            max_currency_length=max_currency_length,
            max_quantity_value=max_quantity_value,
            max_price_value=max_price_value,
            max_filename_length=max_filename_length,
            allowed_extensions=allowed_extensions,
        )

        logger.info(
            "Loaded security configuration: max_file_size=%sMB, max_ticker_length=%s, allowed_extensions=%s",
            max_file_size_mb,
            max_ticker_length,
            allowed_extensions,
        )

        return security_config

    except (KeyError, ValueError) as e:
        logger.warning("Failed to load security configuration, using defaults: %s", e)
        return DEFAULT_SECURITY_CONFIG
