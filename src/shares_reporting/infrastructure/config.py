import configparser
from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple, List
from pathlib import Path

from .logging_config import get_logger
from .validation import SecurityConfig, DEFAULT_SECURITY_CONFIG


class ConversionRate(NamedTuple):
    base: str
    calculated: str
    rate: Decimal


@dataclass
class Config:
    base: str
    rates: List[ConversionRate]
    security: SecurityConfig = None

    def __post_init__(self):
        if self.security is None:
            self.security = DEFAULT_SECURITY_CONFIG


# https://docs.python.org/3/library/configparser.html
def create_config():
    logger = get_logger(__name__)
    config = configparser.ConfigParser()
    config.optionxform = str
    config.allow_no_value = True
    config["COMMON"] = {"TARGET CURRENCY": "EUR", "YEAR": "2022"}
    config["EXCHANGE RATES"] = {"EUR/CAD": "0.69252",
                                "EUR/USD": "0.93756",
                                "EUR/GBP": "1.12748",
                                "EUR/HKD": "0.12025",
                                "EUR/PLN": "0.21364"}
    config["SECURITY"] = {
        "MAX_FILE_SIZE_MB": "100",
        "MAX_TICKER_LENGTH": "10",
        "MAX_CURRENCY_LENGTH": "3",
        "MAX_QUANTITY_VALUE": "10000000000",
        "MAX_PRICE_VALUE": "1000000000",
        "MAX_FILENAME_LENGTH": "255",
        "ALLOWED_EXTENSIONS": ".csv,.txt"
    }

    config_path = 'config.ini'
    try:
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        logger.info(f"Created default configuration file: {config_path}")
        logger.info("Configuration includes 5 exchange rates for EUR base currency and security settings")
    except OSError as e:
        logger.error(f"Failed to create configuration file {config_path}: {e}")
        raise


def read_config() -> Config:
    logger = get_logger(__name__)
    config = configparser.ConfigParser()
    config.optionxform = str

    config_path = 'config.ini'
    try:
        files_read = config.read(config_path)
        if not files_read:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        logger.info(f"Loaded configuration from {config_path}")
        logger.debug(f"Available sections: {list(config.sections())}")

    except (configparser.Error, OSError) as e:
        logger.error(f"Failed to read configuration file {config_path}: {e}")
        raise

    try:
        target: str = config["COMMON"]["TARGET CURRENCY"]
        logger.debug(f"Target currency: {target}")

        rates: List[ConversionRate] = []
        for key in config["EXCHANGE RATES"]:
            base, calculated = key.split("/")
            assert base == target
            rate_value = Decimal(config["EXCHANGE RATES"][key])
            rates.append(ConversionRate(base=base, calculated=calculated, rate=rate_value))
            logger.debug(f"Loaded exchange rate {key} = {rate_value}")

        logger.info(f"Loaded {len(rates)} exchange rates for base currency {target}")

        # Load security settings
        security_config = _load_security_config(config, logger)

        return Config(base=target, rates=rates, security=security_config)

    except (KeyError, ValueError, AssertionError) as e:
        logger.error(f"Configuration parsing error: {e}")
        raise


def _load_security_config(config: configparser.ConfigParser, logger) -> SecurityConfig:
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
            allowed_extensions=allowed_extensions
        )

        logger.info(f"Loaded security configuration: max_file_size={max_file_size_mb}MB, "
                   f"max_ticker_length={max_ticker_length}, allowed_extensions={allowed_extensions}")

        return security_config

    except (KeyError, ValueError) as e:
        logger.warning(f"Failed to load security configuration, using defaults: {e}")
        return DEFAULT_SECURITY_CONFIG


def main():
    create_config()


if __name__ == "__main__":
    main()
