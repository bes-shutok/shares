"""Context classes for processing different sections of the IB CSV export."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from ...domain.constants import (
    ASSET_CATEGORY_COLUMN_INDEX,
    CSV_DATA_MARKER,
    CSV_HEADER_MARKER,
    DATA_DISCRIMINATOR_COLUMN_INDEX,
    FINANCIAL_INSTRUMENT_MIN_COLUMNS,
    ISIN_DATA_COLUMN_INDEX,
    SYMBOL_COLUMN_INDEX,
    ZERO_QUANTITY,
)
from ...domain.exceptions import FileProcessingError
from ...infrastructure.isin_country import isin_to_country
from ...infrastructure.logging_config import create_module_logger

if TYPE_CHECKING:
    from logging import Logger

MIN_HEADER_LENGTH = DATA_DISCRIMINATOR_COLUMN_INDEX
MIN_FINANCIAL_INSTRUMENT_HEADER_LENGTH = 7
FINANCIAL_INSTRUMENT_DATA_LENGTH = FINANCIAL_INSTRUMENT_MIN_COLUMNS
LOG_SAMPLE_SIZE = 5


class BaseSectionContext:
    """Base class for CSV section processing contexts."""

    logger: Logger
    headers_found: bool
    processed_count: int

    def __init__(self):
        """Initialize the base section context."""
        self.logger = create_module_logger(self.__class__.__name__)
        self.headers_found = False
        self.processed_count = 0

    def process_header(self, _row: list[str], _row_number: int) -> None:
        """Process section header row."""
        raise NotImplementedError("Subclasses must implement process_header")

    def process_data_row(self, _row: list[str], _row_number: int) -> None:
        """Process section data row."""
        raise NotImplementedError("Subclasses must implement process_data_row")

    def validate_header(self, _row: list[str]) -> bool:
        """Validate if this row is a valid header for this section."""
        return True

    def can_process_row(self, _row: list[str]) -> bool:
        """Check if this context can process the given row."""
        return self.headers_found

    def finish(self) -> None:
        """Called when section processing is complete."""
        pass


class FinancialInstrumentContext(BaseSectionContext):
    """Context for processing Financial Instrument Information section."""

    security_info: dict[str, dict[str, str]]
    security_processed_count: int
    processed_count: int
    headers_found: bool

    def __init__(self, security_info: dict[str, dict[str, str]]):
        """Initialize the Financial Instrument context.

        Args:
            security_info: Dictionary to store extracted security information.
        """
        super().__init__()
        self.security_info = security_info
        self.security_processed_count = 0
        self.processed_count = 0

    @override
    def process_header(self, row: list[str], row_number: int) -> None:
        """Process Financial Instrument Information header."""
        if (
            len(row) >= MIN_FINANCIAL_INSTRUMENT_HEADER_LENGTH
            and row[1] == CSV_HEADER_MARKER
            and row[3] == "Symbol"
            and row[6] == "Security ID"
        ):
            self.headers_found = True
            self.logger.debug("Found Financial Instrument Information header")
        else:
            raise FileProcessingError(
                "Row %d: Invalid 'Financial Instrument Information' header format: %s", row_number, row
            )

    MIN_SYMBOL_INDEX: int = SYMBOL_COLUMN_INDEX
    MIN_ISIN_INDEX: int = ISIN_DATA_COLUMN_INDEX

    @override
    def process_data_row(self, row: list[str], row_number: int) -> None:
        """Process security info data row."""
        if not self.can_process_row(row):
            return

        if (
            len(row) >= FINANCIAL_INSTRUMENT_DATA_LENGTH
            and row[1] == CSV_DATA_MARKER
            and row[DATA_DISCRIMINATOR_COLUMN_INDEX] == "Stocks"
        ):
            symbol = row[3] if len(row) > self.MIN_SYMBOL_INDEX else ""
            isin = row[6] if len(row) > self.MIN_ISIN_INDEX else ""

            if symbol and isin:
                try:
                    country = isin_to_country(isin)
                    self.security_info[symbol] = {"isin": isin, "country": country}
                    self.security_processed_count += 1
                    self.processed_count += 1
                    self.logger.debug("Extracted security info for %s: %s (%s)", symbol, isin, country)
                except Exception as e:
                    self.logger.warning(
                        "Row %d: Failed to extract country for %s with ISIN %s: %s",
                        row_number,
                        symbol,
                        isin,
                        e,
                    )
                    self.security_info[symbol] = {"isin": isin, "country": "Unknown"}
                    self.processed_count += 1

    @override
    def validate_header(self, row: list[str]) -> bool:
        """Validate Financial Instrument Information header."""
        return (
            len(row) >= MIN_HEADER_LENGTH
            and row[0] == "Financial Instrument Information"
            and row[1] == CSV_HEADER_MARKER
        )


class TradesContext(BaseSectionContext):
    """Context for processing Trades section."""

    raw_trade_data: list[dict[str, str]]
    require_trades_section: bool
    trades_headers: list[str] | None
    trades_col_mapping: dict[str, int | None] | None
    invalid_trades: int
    processed_count: int
    headers_found: bool

    def __init__(self, raw_trade_data: list[dict[str, str]], require_trades_section: bool = True):
        """Initialize the Trades context.

        Args:
            raw_trade_data: List to store extracted trade data.
            require_trades_section: Whether to enforce presence of Trades section.
        """
        super().__init__()
        self.raw_trade_data = raw_trade_data
        self.require_trades_section = require_trades_section
        self.trades_headers = None
        self.trades_col_mapping = None
        self.invalid_trades = ZERO_QUANTITY  # Only count data quality issues (missing symbol/datetime)
        self.processed_count = 0

    @override
    def process_header(self, row: list[str], row_number: int) -> None:
        """Process Trades section header."""
        if len(row) >= MIN_HEADER_LENGTH and row[1] == CSV_HEADER_MARKER:
            self.trades_headers = row
            self.logger.debug("Found Trades section header")

            # Create column mapping
            try:
                # Handle different fee column names
                fee_column: int | None = None
                if "Comm/Fee" in self.trades_headers:
                    fee_column = self.trades_headers.index("Comm/Fee")
                elif "Comm in EUR" in self.trades_headers:
                    fee_column = self.trades_headers.index("Comm in EUR")
                elif "Commission" in self.trades_headers:
                    fee_column = self.trades_headers.index("Commission")

                self.trades_col_mapping = {
                    "symbol": self.trades_headers.index("Symbol"),
                    "currency": self.trades_headers.index("Currency"),
                    "datetime": self.trades_headers.index("Date/Time"),
                    "quantity": self.trades_headers.index("Quantity"),
                    "price": self.trades_headers.index("T. Price"),
                    "fee": fee_column,
                }
                self.headers_found = True
                self.logger.debug("Column mapping: %s", self.trades_col_mapping)
            except ValueError as e:
                if self.require_trades_section:
                    raise FileProcessingError(
                        "Row %d: Missing required column in Trades section: %s", row_number, e
                    ) from e
                else:
                    # If trades section is not required, just skip it
                    self.logger.debug("Row %d: Skipping Trades section due to missing columns: %s", row_number, e)
                    self.trades_headers = None
                    self.trades_col_mapping = None
        else:
            raise FileProcessingError("Row %d: Invalid Trades header format", row_number)

    @override
    def process_data_row(self, row: list[str], row_number: int) -> None:
        """Process trade data row."""
        if not self.can_process_row(row) or not self.trades_col_mapping or not self.trades_headers:
            return

        # Validate row format - fail fast on invalid data with full context
        if len(row) < len(self.trades_headers):
            error_msg = (
                f"Invalid trade data format detected at CSV row {row_number}!\n"
                f"Expected {len(self.trades_headers)} columns but found {len(row)}.\n"
                f"Header: {self.trades_headers}\n"
                f"Actual data: {row}\n"
                f"This indicates corrupted or incomplete IB export data. "
                f"Please verify your IB export file integrity."
            )
            self.logger.error(error_msg)
            raise FileProcessingError(error_msg)

        # Filter 2: Non-stock orders (options, forex, etc.) - filter out asset types
        if len(row) > MIN_HEADER_LENGTH and (
            row[DATA_DISCRIMINATOR_COLUMN_INDEX] != "Order" or row[ASSET_CATEGORY_COLUMN_INDEX] != "Stocks"
        ):
            return

        # Extract trade data as dictionary for deferred processing
        fee_value = ""
        fee_idx = self.trades_col_mapping["fee"]
        if fee_idx is not None and len(row) > fee_idx:
            fee_value = row[fee_idx]

        # Extract indices safely, ensuring they are not None
        symbol_idx = self.trades_col_mapping["symbol"]
        currency_idx = self.trades_col_mapping["currency"]
        datetime_idx = self.trades_col_mapping["datetime"]
        quantity_idx = self.trades_col_mapping["quantity"]
        price_idx = self.trades_col_mapping["price"]

        # These should never be None for required columns
        if (
            symbol_idx is None
            or currency_idx is None
            or datetime_idx is None
            or quantity_idx is None
            or price_idx is None
        ):
            self.logger.error("Row %d: Missing required column index in trades mapping", row_number)
            return

        trade_row: dict[str, str] = {
            "symbol": row[symbol_idx] if len(row) > symbol_idx else "",
            "currency": row[currency_idx] if len(row) > currency_idx else "",
            "datetime": row[datetime_idx] if len(row) > datetime_idx else "",
            "quantity": row[quantity_idx] if len(row) > quantity_idx else "",
            "price": row[price_idx] if len(row) > price_idx else "",
            "fee": fee_value,
        }

        # Validation: Check for missing critical data (data quality issue)
        if not trade_row["symbol"] or not trade_row["datetime"] or trade_row["datetime"].strip() == "":
            self.invalid_trades += 1
            return

        self.raw_trade_data.append(trade_row)
        self.processed_count += 1

        if self.processed_count <= LOG_SAMPLE_SIZE or self.processed_count % 100 == 0:
            self.logger.debug(
                "Collected trade %s: %s %s %s @ %s",
                self.processed_count,
                trade_row["symbol"],
                trade_row["currency"],
                trade_row["quantity"],
                trade_row["price"],
            )

    @override
    def validate_header(self, row: list[str]) -> bool:
        """Validate Trades header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Trades" and row[1] == CSV_HEADER_MARKER


class DividendsContext(BaseSectionContext):
    """Context for processing Dividends section."""

    raw_dividend_data: list[dict[str, str]]
    dividends_headers: list[str] | None
    dividends_col_mapping: dict[str, int] | None
    headers_found: bool
    processed_count: int

    def __init__(self, raw_dividend_data: list[dict[str, str]]):
        """Initialize the Dividends context.

        Args:
            raw_dividend_data: List to store extracted dividend data.
        """
        super().__init__()
        self.raw_dividend_data = raw_dividend_data
        self.dividends_headers = None
        self.dividends_col_mapping = None

    @override
    def process_header(self, row: list[str], row_number: int) -> None:
        """Process Dividends section header."""
        if len(row) >= MIN_HEADER_LENGTH and row[1] == CSV_HEADER_MARKER:
            self.dividends_headers = row
            self.logger.debug("Found Dividends section header")

            # Create column mapping
            try:
                self.dividends_col_mapping = {
                    "currency": self.dividends_headers.index("Currency"),
                    "date": self.dividends_headers.index("Date"),
                    "description": self.dividends_headers.index("Description"),
                    "amount": self.dividends_headers.index("Amount"),
                }
                self.headers_found = True
                self.logger.debug("Dividend column mapping: %s", self.dividends_col_mapping)
            except ValueError as e:
                self.logger.debug("Row %d: Skipping Dividends section due to missing columns: %s", row_number, e)
                self.dividends_headers = None
                self.dividends_col_mapping = None
        else:
            raise FileProcessingError("Row %d: Invalid Dividends header format", row_number)

    @override
    def process_data_row(self, row: list[str], row_number: int) -> None:
        """Process dividend data row."""
        if not self.can_process_row(row) or not self.dividends_col_mapping:
            return

        currency_idx = self.dividends_col_mapping["currency"]
        date_idx = self.dividends_col_mapping["date"]
        description_idx = self.dividends_col_mapping["description"]
        amount_idx = self.dividends_col_mapping["amount"]

        dividend_row: dict[str, str] = {
            "currency": row[currency_idx] if len(row) > currency_idx else "",
            "date": row[date_idx] if len(row) > date_idx else "",
            "description": row[description_idx] if len(row) > description_idx else "",
            "amount": row[amount_idx] if len(row) > amount_idx else "",
        }

        if dividend_row["description"] and dividend_row["amount"]:
            self.raw_dividend_data.append(dividend_row)
            self.processed_count += 1

            if self.processed_count <= LOG_SAMPLE_SIZE:
                self.logger.debug(
                    "Row %d: Collected dividend %s: %s %s %s",
                    row_number,
                    self.processed_count,
                    dividend_row["description"],
                    dividend_row["currency"],
                    dividend_row["amount"],
                )

    @override
    def validate_header(self, row: list[str]) -> bool:
        """Validate Dividends header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Dividends" and row[1] == CSV_HEADER_MARKER


class WithholdingTaxContext(BaseSectionContext):
    """Context for processing Withholding Tax section."""

    raw_withholding_tax_data: list[dict[str, str]]
    withholding_tax_headers: list[str] | None
    withholding_tax_col_mapping: dict[str, int] | None
    headers_found: bool
    processed_count: int

    def __init__(self, raw_withholding_tax_data: list[dict[str, str]]):
        """Initialize the Withholding Tax context.

        Args:
            raw_withholding_tax_data: List to store extracted withholding tax data.
        """
        super().__init__()
        self.raw_withholding_tax_data = raw_withholding_tax_data
        self.withholding_tax_headers = None
        self.withholding_tax_col_mapping = None

    @override
    def process_header(self, row: list[str], row_number: int) -> None:
        """Process Withholding Tax section header."""
        if len(row) >= MIN_HEADER_LENGTH and row[1] == CSV_HEADER_MARKER:
            self.withholding_tax_headers = row
            self.logger.debug("Found Withholding Tax section header")

            # Create column mapping (skip Code column as it's always empty)
            try:
                self.withholding_tax_col_mapping = {
                    "currency": self.withholding_tax_headers.index("Currency"),
                    "date": self.withholding_tax_headers.index("Date"),
                    "description": self.withholding_tax_headers.index("Description"),
                    "amount": self.withholding_tax_headers.index("Amount"),
                }
                self.headers_found = True
                self.logger.debug(
                    "Withholding Tax column mapping: %s",
                    self.withholding_tax_col_mapping,
                )
            except ValueError as e:
                self.logger.debug("Row %d: Skipping Withholding Tax section due to missing columns: %s", row_number, e)
                self.withholding_tax_headers = None
                self.withholding_tax_col_mapping = None
        else:
            raise FileProcessingError("Row %d: Invalid Withholding Tax header format", row_number)

    @override
    def process_data_row(self, row: list[str], row_number: int) -> None:
        """Process withholding tax data row."""
        if not self.can_process_row(row) or not self.withholding_tax_col_mapping:
            return

        currency_idx = self.withholding_tax_col_mapping["currency"]
        date_idx = self.withholding_tax_col_mapping["date"]
        description_idx = self.withholding_tax_col_mapping["description"]
        amount_idx = self.withholding_tax_col_mapping["amount"]

        tax_row: dict[str, str] = {
            "currency": row[currency_idx] if len(row) > currency_idx else "",
            "date": row[date_idx] if len(row) > date_idx else "",
            "description": row[description_idx] if len(row) > description_idx else "",
            "amount": row[amount_idx] if len(row) > amount_idx else "",
        }

        if tax_row["description"] and tax_row["amount"]:
            self.raw_withholding_tax_data.append(tax_row)
            self.processed_count += 1

            if self.processed_count <= LOG_SAMPLE_SIZE:
                self.logger.debug(
                    "Row %d: Collected withholding tax %s: %s %s %s",
                    row_number,
                    self.processed_count,
                    tax_row["description"],
                    tax_row["currency"],
                    tax_row["amount"],
                )

    @override
    def validate_header(self, row: list[str]) -> bool:
        """Validate Withholding Tax header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Withholding Tax" and row[1] == CSV_HEADER_MARKER
