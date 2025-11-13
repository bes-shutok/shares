"""
Input validation and file path sanitization utilities.

Provides secure validation functions for file operations and user input.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from ..domain.constants import TICKER_FORMAT_PATTERN, CURRENCY_FORMAT_PATTERN
from ..infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class SecurityError(Exception):
    """Raised when a security issue is detected."""
    pass


@dataclass
class SecurityConfig:
    """Configuration for security validation limits."""
    max_file_size_mb: int = 100
    max_ticker_length: int = 10
    max_currency_length: int = 3
    max_quantity_value: int = 10_000_000_000  # 10 billion shares
    max_price_value: int = 1_000_000_000  # 1 billion currency units
    max_filename_length: int = 255
    allowed_extensions: List[str] = None
    blocked_patterns: List[str] = None

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.csv', '.txt']
        if self.blocked_patterns is None:
            self.blocked_patterns = [
                r'\.\.[\\/]',  # Directory traversal
                r'[<>:"|?*]',  # Invalid filename characters
                r'\0',  # Null bytes
                r'^CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]$',  # Reserved Windows names
            ]


# Default security configuration
DEFAULT_SECURITY_CONFIG = SecurityConfig()


def sanitize_file_path(
    file_path: Union[str, Path],
    allowed_directories: Optional[List[Path]] = None,
    config: SecurityConfig = DEFAULT_SECURITY_CONFIG
) -> Path:
    """
    Sanitize and validate file paths to prevent directory traversal attacks.

    Args:
        file_path: The file path to validate
        allowed_directories: List of allowed base directories (if None, only allows relative paths)
        config: Security configuration with validation limits

    Returns:
        Sanitized absolute Path object
    """
    try:
        # Convert to Path object if it's a string
        path_obj = Path(file_path)

        # Validate filename length
        if len(path_obj.name) > config.max_filename_length:
            raise ValidationError(f"Filename too long (max {config.max_filename_length} characters): {path_obj.name}")

        # Check file extension
        if path_obj.suffix.lower() not in config.allowed_extensions:
            raise ValidationError(f"File extension not allowed: {path_obj.suffix}. Allowed: {config.allowed_extensions}")

        # Convert to absolute path
        abs_path = path_obj.resolve()

        # Check for dangerous patterns using configurable patterns
        path_str = str(file_path)
        for pattern in config.blocked_patterns:
            if re.search(pattern, path_str, re.IGNORECASE):
                logger.warning(f"Blocked dangerous path pattern: {pattern} in {file_path}")
                raise SecurityError(f"Potentially dangerous path detected: {file_path}")

        # If allowed directories are specified, ensure path is within them
        if allowed_directories:
            allowed = False
            for allowed_dir in allowed_directories:
                allowed_abs = allowed_dir.resolve()
                try:
                    abs_path.relative_to(allowed_abs)
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                raise SecurityError(f"Path not in allowed directories: {file_path}")

        # Additional safety checks
        if not abs_path.parent.exists():
            raise ValidationError(f"Parent directory does not exist: {abs_path.parent}")

        return abs_path

    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid file path {file_path}: {str(e)}")


def validate_csv_file(file_path: Union[str, Path], config: SecurityConfig = DEFAULT_SECURITY_CONFIG) -> Path:
    """
    Validate that a file is a valid CSV file for processing.

    Args:
        file_path: Path to the CSV file
        config: Security configuration with validation limits

    Returns:
        Sanitized Path object
    """
    # Sanitize path first
    safe_path = sanitize_file_path(file_path, config=config)

    # Check if file exists
    if not safe_path.exists():
        raise ValidationError(f"File does not exist: {safe_path}")

    # Check if it's a file (not directory)
    if not safe_path.is_file():
        raise ValidationError(f"Path is not a file: {safe_path}")

    # Check file size (prevent extremely large files)
    max_size_bytes = config.max_file_size_mb * 1024 * 1024
    if safe_path.stat().st_size > max_size_bytes:
        raise ValidationError(f"File too large (max {config.max_file_size_mb}MB): {safe_path}")

    # Try to read first few lines to ensure it's readable
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            # Read first 1024 bytes to check if it's text
            sample = f.read(1024)
            if not sample.strip():
                raise ValidationError(f"File appears to be empty: {safe_path}")

            # Check for binary content (heuristic)
            if '\x00' in sample:  # Null bytes indicate binary
                raise ValidationError(f"File appears to be binary, not CSV: {safe_path}")

    except UnicodeDecodeError:
        raise ValidationError(f"File encoding error (not UTF-8): {safe_path}")
    except PermissionError:
        raise ValidationError(f"Permission denied reading file: {safe_path}")
    except OSError as e:
        raise ValidationError(f"Error reading file {safe_path}: {str(e)}")

    logger.info(f"Validated CSV file: {safe_path}")
    return safe_path


def sanitize_directory_path(
    directory_path: Union[str, Path],
    config: SecurityConfig = DEFAULT_SECURITY_CONFIG
) -> Path:
    """
    Sanitize and validate directory paths to prevent directory traversal attacks.

    Args:
        directory_path: The directory path to validate
        config: Security configuration with validation limits

    Returns:
        Sanitized absolute Path object
    """
    try:
        # Convert to Path object if it's a string
        path_obj = Path(directory_path)

        # Validate directory name length
        if len(path_obj.name) > config.max_filename_length:
            raise ValidationError(f"Directory name too long (max {config.max_filename_length} characters): {path_obj.name}")

        # Convert to absolute path
        abs_path = path_obj.resolve()

        # Check for dangerous patterns using configurable patterns
        path_str = str(directory_path)
        for pattern in config.blocked_patterns:
            if re.search(pattern, path_str, re.IGNORECASE):
                logger.warning(f"Blocked dangerous path pattern: {pattern} in {directory_path}")
                raise SecurityError(f"Potentially dangerous path detected: {directory_path}")

        return abs_path

    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid directory path {directory_path}: {str(e)}")


def validate_output_directory(output_path: Union[str, Path]) -> Path:
    """
    Validate and create output directory if needed.

    Args:
        output_path: Path to output directory

    Returns:
        Sanitized Path object
    """
    # Sanitize directory path (not file path)
    safe_path = sanitize_directory_path(output_path)

    try:
        # Create directory if it doesn't exist
        safe_path.mkdir(parents=True, exist_ok=True)

        # Check if we can write to the directory
        test_file = safe_path / '.write_test'
        test_file.touch()
        test_file.unlink()

        logger.info(f"Validated output directory: {safe_path}")
        return safe_path

    except PermissionError:
        raise ValidationError(f"Permission denied creating/writing directory: {safe_path}")
    except OSError as e:
        raise ValidationError(f"Error creating directory {safe_path}: {str(e)}")


def validate_company_ticker(ticker: str, config: SecurityConfig = DEFAULT_SECURITY_CONFIG) -> str:
    """
    Validate company ticker symbol.

    Args:
        ticker: Company ticker string
        config: Security configuration with validation limits

    Returns:
        Validated ticker string
    """
    if not ticker:
        raise ValidationError("Company ticker cannot be empty")

    # Remove whitespace and convert to uppercase
    clean_ticker = ticker.strip().upper()

    # Check basic ticker format using constant pattern
    if not re.match(TICKER_FORMAT_PATTERN, clean_ticker):
        raise ValidationError(f"Invalid ticker format: '{ticker}'")

    if len(clean_ticker) > config.max_ticker_length:
        raise ValidationError(f"Ticker too long (max {config.max_ticker_length} characters): '{ticker}'")

    return clean_ticker


def validate_currency_code(currency: str, config: SecurityConfig = DEFAULT_SECURITY_CONFIG) -> str:
    """
    Validate currency code.

    Args:
        currency: Currency code string
        config: Security configuration with validation limits

    Returns:
        Validated currency code
    """
    if not currency:
        raise ValidationError("Currency code cannot be empty")

    # Remove whitespace and convert to uppercase
    clean_currency = currency.strip().upper()

    # Check currency format using constant pattern
    if not re.match(CURRENCY_FORMAT_PATTERN, clean_currency):
        raise ValidationError(f"Invalid currency code format: '{currency}' (must be {config.max_currency_length} letters)")

    return clean_currency


def validate_quantity(quantity_str: str, config: SecurityConfig = DEFAULT_SECURITY_CONFIG) -> float:
    """
    Validate and parse trade quantity.

    Args:
        quantity_str: Quantity as string
        config: Security configuration with validation limits

    Returns:
        Validated quantity as float
    """
    if not quantity_str:
        raise ValidationError("Quantity cannot be empty")

    try:
        # Remove commas and convert to float
        clean_quantity = quantity_str.replace(',', '')
        quantity = float(clean_quantity)

        # Check for reasonable bounds using configurable limit
        if abs(quantity) > config.max_quantity_value:
            raise ValidationError(f"Quantity too large: {quantity}")

        return quantity

    except ValueError:
        raise ValidationError(f"Invalid quantity format: '{quantity_str}'")


def validate_price(price_str: str, config: SecurityConfig = DEFAULT_SECURITY_CONFIG) -> float:
    """
    Validate and parse trade price.

    Args:
        price_str: Price as string
        config: Security configuration with validation limits

    Returns:
        Validated price as float
    """
    if not price_str:
        raise ValidationError("Price cannot be empty")

    try:
        # Remove commas and convert to float
        clean_price = price_str.replace(',', '')
        price = float(clean_price)

        # Check for reasonable bounds
        if price < 0:
            raise ValidationError(f"Price cannot be negative: {price}")

        if price > config.max_price_value:  # Use configurable limit
            raise ValidationError(f"Price too large: {price}")

        return price

    except ValueError:
        raise ValidationError(f"Invalid price format: '{price_str}'")
