"""Context classes for processing different sections of the IB CSV export."""
from __future__ import annotations

from ...domain.exceptions import FileProcessingError
from ...infrastructure.isin_country import isin_to_country
from ...infrastructure.logging_config import create_module_logger

MIN_HEADER_LENGTH = 2
MIN_FINANCIAL_INSTRUMENT_HEADER_LENGTH = 7
MIN_FINANCIAL_INSTRUMENT_DATA_LENGTH = 7
LOG_SAMPLE_SIZE = 5

class BaseSectionContext:
    """Base class for CSV section processing contexts."""

    def __init__(self):
        """Initialize the base section context."""
        self.logger = create_module_logger(self.__class__.__name__)
        self.headers_found = False
        self.processed_count = 0

    def process_header(self, row: list[str]) -> None:
        """Process section header row."""
        raise NotImplementedError("Subclasses must implement process_header")

    def process_data_row(self, row: list[str]) -> None:
        """Process section data row."""
        raise NotImplementedError("Subclasses must implement process_data_row")

    def validate_header(self, row: list[str]) -> bool:
        """Validate if this row is a valid header for this section."""
        return True

    def can_process_row(self, row: list[str]) -> bool:
        """Check if this context can process the given row."""
        return self.headers_found

    def finish(self) -> None:
        """Called when section processing is complete."""
        pass


class FinancialInstrumentContext(BaseSectionContext):
    """Context for processing Financial Instrument Information section."""

    def __init__(self, security_info: dict[str, dict[str, str]]):
        """Initialize the Financial Instrument context.

        Args:
            security_info: Dictionary to store extracted security information.
        """
        super().__init__()
        self.security_info = security_info
        self.security_processed_count = 0

    def process_header(self, row: list[str]) -> None:
        """Process Financial Instrument Information header."""
        if (
            len(row) >= MIN_FINANCIAL_INSTRUMENT_HEADER_LENGTH
            and row[1] == "Header"
            and row[3] == "Symbol"
            and row[6] == "Security ID"
        ):
            self.headers_found = True
            self.logger.debug("Found Financial Instrument Information header")
        else:
            raise FileProcessingError(
                f"Invalid 'Financial Instrument Information' header format: {row}"
            )

    MIN_SYMBOL_INDEX = 3
    MIN_ISIN_INDEX = 6

    def process_data_row(self, row: list[str]) -> None:
        """Process security info data row."""
        if not self.can_process_row(row):
            return

        if len(row) >= MIN_FINANCIAL_INSTRUMENT_DATA_LENGTH and row[1] == "Data" and row[2] == "Stocks":
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
                        f"Failed to extract country for {symbol} with ISIN {isin}: {e}"
                    )
                    self.security_info[symbol] = {"isin": isin, "country": "Unknown"}
                    self.processed_count += 1

    def validate_header(self, row: list[str]) -> bool:
        """Validate Financial Instrument Information header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Financial Instrument Information" and row[1] == "Header"


class TradesContext(BaseSectionContext):
    """Context for processing Trades section."""

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
        self.skipped_trades = 0

    def process_header(self, row: list[str]) -> None:
        """Process Trades section header."""
        if len(row) >= MIN_HEADER_LENGTH and row[1] == "Header":
            self.trades_headers = row
            self.logger.debug("Found Trades section header")

            # Create column mapping
            try:
                # Handle different fee column names
                fee_column = None
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
                        f"Missing required column in Trades section: {e}"
                    ) from e
                else:
                    # If trades section is not required, just skip it
                    self.logger.debug("Skipping Trades section due to missing columns: %s", e)
                    self.trades_headers = None
                    self.trades_col_mapping = None
        else:
            raise FileProcessingError("Invalid Trades header format")

    def process_data_row(self, row: list[str]) -> None:
        """Process trade data row."""
        if not self.can_process_row(row) or not self.trades_col_mapping:
            return

        if len(row) < len(self.trades_headers):
            self.skipped_trades += 1
            return

        if len(row) > MIN_HEADER_LENGTH and (row[2] != "Order" or row[3] != "Stocks"):
            self.skipped_trades += 1
            return

        # Extract trade data as dictionary for deferred processing
        fee_value = ""
        if self.trades_col_mapping["fee"] is not None:
            fee_value = (
                row[self.trades_col_mapping["fee"]]
                if len(row) > self.trades_col_mapping["fee"]
                else ""
            )

        trade_row = {
            "symbol": row[self.trades_col_mapping["symbol"]]
            if len(row) > self.trades_col_mapping["symbol"]
            else "",
            "currency": row[self.trades_col_mapping["currency"]]
            if len(row) > self.trades_col_mapping["currency"]
            else "",
            "datetime": row[self.trades_col_mapping["datetime"]]
            if len(row) > self.trades_col_mapping["datetime"]
            else "",
            "quantity": row[self.trades_col_mapping["quantity"]]
            if len(row) > self.trades_col_mapping["quantity"]
            else "",
            "price": row[self.trades_col_mapping["price"]]
            if len(row) > self.trades_col_mapping["price"]
            else "",
            "fee": fee_value,
        }

        if (
            not trade_row["symbol"]
            or not trade_row["datetime"]
            or trade_row["datetime"].strip() == ""
        ):
            self.skipped_trades += 1
            return

        self.raw_trade_data.append(trade_row)
        self.processed_count += 1

        if self.processed_count <= LOG_SAMPLE_SIZE or self.processed_count % 100 == 0:
            self.logger.debug(
                f"Collected trade {self.processed_count}: {trade_row['symbol']} "
                f"{trade_row['currency']} {trade_row['quantity']} @ {trade_row['price']}"
            )

    def validate_header(self, row: list[str]) -> bool:
        """Validate Trades header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Trades" and row[1] == "Header"


class DividendsContext(BaseSectionContext):
    """Context for processing Dividends section."""

    def __init__(self, raw_dividend_data: list[dict[str, str]]):
        """Initialize the Dividends context.

        Args:
            raw_dividend_data: List to store extracted dividend data.
        """
        super().__init__()
        self.raw_dividend_data = raw_dividend_data
        self.dividends_headers = None
        self.dividends_col_mapping = None

    def process_header(self, row: list[str]) -> None:
        """Process Dividends section header."""
        if len(row) >= MIN_HEADER_LENGTH and row[1] == "Header":
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
                self.logger.debug("Skipping Dividends section due to missing columns: %s", e)
                self.dividends_headers = None
                self.dividends_col_mapping = None
        else:
            raise FileProcessingError("Invalid Dividends header format")

    def process_data_row(self, row: list[str]) -> None:
        """Process dividend data row."""
        if not self.can_process_row(row) or not self.dividends_col_mapping:
            return

        dividend_row = {
            "currency": row[self.dividends_col_mapping["currency"]]
            if len(row) > self.dividends_col_mapping["currency"]
            else "",
            "date": row[self.dividends_col_mapping["date"]]
            if len(row) > self.dividends_col_mapping["date"]
            else "",
            "description": row[self.dividends_col_mapping["description"]]
            if len(row) > self.dividends_col_mapping["description"]
            else "",
            "amount": row[self.dividends_col_mapping["amount"]]
            if len(row) > self.dividends_col_mapping["amount"]
            else "",
        }

        if dividend_row["description"] and dividend_row["amount"]:
            self.raw_dividend_data.append(dividend_row)
            self.processed_count += 1

            if self.processed_count <= LOG_SAMPLE_SIZE:
                self.logger.debug(
                    f"Collected dividend {self.processed_count}: {dividend_row['description']} "
                    f"{dividend_row['currency']} {dividend_row['amount']}"
                )

    def validate_header(self, row: list[str]) -> bool:
        """Validate Dividends header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Dividends" and row[1] == "Header"


class WithholdingTaxContext(BaseSectionContext):
    """Context for processing Withholding Tax section."""

    def __init__(self, raw_withholding_tax_data: list[dict[str, str]]):
        """Initialize the Withholding Tax context.

        Args:
            raw_withholding_tax_data: List to store extracted withholding tax data.
        """
        super().__init__()
        self.raw_withholding_tax_data = raw_withholding_tax_data
        self.withholding_tax_headers = None
        self.withholding_tax_col_mapping = None

    def process_header(self, row: list[str]) -> None:
        """Process Withholding Tax section header."""
        if len(row) >= MIN_HEADER_LENGTH and row[1] == "Header":
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
                    f"Withholding Tax column mapping: {self.withholding_tax_col_mapping}"
                )
            except ValueError as e:
                self.logger.debug("Skipping Withholding Tax section due to missing columns: %s", e)
                self.withholding_tax_headers = None
                self.withholding_tax_col_mapping = None
        else:
            raise FileProcessingError("Invalid Withholding Tax header format")

    def process_data_row(self, row: list[str]) -> None:
        """Process withholding tax data row."""
        if not self.can_process_row(row) or not self.withholding_tax_col_mapping:
            return

        tax_row = {
            "currency": row[self.withholding_tax_col_mapping["currency"]]
            if len(row) > self.withholding_tax_col_mapping["currency"]
            else "",
            "date": row[self.withholding_tax_col_mapping["date"]]
            if len(row) > self.withholding_tax_col_mapping["date"]
            else "",
            "description": row[self.withholding_tax_col_mapping["description"]]
            if len(row) > self.withholding_tax_col_mapping["description"]
            else "",
            "amount": row[self.withholding_tax_col_mapping["amount"]]
            if len(row) > self.withholding_tax_col_mapping["amount"]
            else "",
        }

        if tax_row["description"] and tax_row["amount"]:
            self.raw_withholding_tax_data.append(tax_row)
            self.processed_count += 1

            if self.processed_count <= LOG_SAMPLE_SIZE:
                self.logger.debug(
                    f"Collected withholding tax {self.processed_count}: {tax_row['description']} "
                    f"{tax_row['currency']} {tax_row['amount']}"
                )

    def validate_header(self, row: list[str]) -> bool:
        """Validate Withholding Tax header."""
        return len(row) >= MIN_HEADER_LENGTH and row[0] == "Withholding Tax" and row[1] == "Header"
