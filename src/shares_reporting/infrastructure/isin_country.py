"""
ISIN country resolution utility.

This module provides functionality to extract country information from ISIN codes.
ISIN (International Securities Identification Number) format:
- First 2 characters: Country code (ISO 3166-1 alpha-2)
- Remaining characters: National security identifier
"""

import pycountry


def isin_to_country_code(isin: str) -> str:
    """
    Convert ISIN code to ISO 3166-1 alpha-2 country code.

    Args:
        isin: The ISIN code (e.g., "US0378331005", "KYG905191022")

    Returns:
        2-letter country code or "Unknown" if invalid.

    Examples:
        >>> isin_to_country_code("US0378331005")
        'US'
        >>> isin_to_country_code("KYG905191022")
        'KY'
        >>> isin_to_country_code("INVALID")
        'Unknown'
        >>> isin_to_country_code("")
        'Unknown'
    """
    if not isin or len(isin) < 2:
        return "Unknown"

    return isin[:2].upper()


def isin_to_country(isin: str) -> str:
    """
    Convert ISIN code to country name.

    Args:
        isin: The ISIN code (e.g., "US0378331005", "KYG905191022")

    Returns:
        Country name (e.g., "United States", "Cayman Islands") or "Unknown" if not found.

    Examples:
        >>> isin_to_country("US0378331005")
        'United States'
        >>> isin_to_country("KYG905191022")
        'Cayman Islands'
        >>> isin_to_country("INVALID")
        'Unknown'
        >>> isin_to_country("")
        'Unknown'
    """
    country_code = isin_to_country_code(isin)

    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else "Unknown"
    except Exception:
        return "Unknown"


def is_valid_isin_format(isin: str) -> bool:
    """
    Check if the string has a valid ISIN format (basic length check).

    Note: This is a basic format check. A full ISIN validation would include
    Luhn algorithm validation of the check digit, which is more complex.

    Args:
        isin: The ISIN code to validate

    Returns:
        True if basic format is valid, False otherwise
    """
    if not isin:
        return False

    # ISIN should be 12 characters: 2-letter country code + 9-character national identifier + 1 check digit
    if len(isin) != 12:
        return False

    # First 2 characters should be letters
    if not isin[:2].isalpha():
        return False

    # Next 9 characters should be alphanumeric
    if not isin[2:11].isalnum():
        return False

    # Last character should be a digit (check digit)
    if not isin[11].isdigit():
        return False

    return True
