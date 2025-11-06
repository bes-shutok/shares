"""
Domain constants for the shares reporting application.

Contains business logic constants that are used throughout the application.
"""
from decimal import Decimal

# Currency and market constants
CURRENCY_CODE_LENGTH = 3
MAX_TICKER_LETTERS = 5
TICKER_FORMAT_PATTERN = r'^[A-Z]{1,5}[0-9]*$'
CURRENCY_FORMAT_PATTERN = r'^[A-Z]{3}$'

# File processing constants
DEFAULT_LOG_LEVEL = "INFO"
LOG_PROGRESS_INTERVAL = 100  # Log progress every N trades
INITIAL_DEBUG_TRADES = 5     # Show first N trades in debug mode

# CSV/Excel column indices
SYMBOL_COLUMN_INDEX = 3
ASSET_CATEGORY_COLUMN_INDEX = 3
DATA_DISCRIMINATOR_COLUMN_INDEX = 2

# Excel report constants
EXCEL_START_COLUMN = 3
EXCEL_START_ROW = 3
EXCEL_HEADER_ROW_1 = 1
EXCEL_HEADER_ROW_2 = 2
EXCEL_WITHOLDING_TAX_COLUMN = 11
EXCEL_COUNTRY_COLUMN = 2
EXCEL_COLUMN_OFFSET = 3

# Excel cell formatting
EXCEL_NUMBER_FORMAT = "0.000000"

# ISIN processing constants
ISIN_DATA_COLUMN_INDEX = 6
FINANCIAL_INSTRUMENT_MIN_COLUMNS = 7

# Trade validation constants
ZERO_QUANTITY = 0
DECIMAL_ZERO = Decimal('0')