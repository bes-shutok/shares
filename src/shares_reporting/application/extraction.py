import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path

from ..domain.collections import (
    DividendIncomePerCompany,
    IBExportData,
    QuantitatedTradeActions,
    TradeCyclePerCompany,
)
from ..domain.entities import (
    CurrencyCompany,
    DividendIncomePerSecurity,
    QuantitatedTradeAction,
    TradeAction,
    TradeCycle,
)
from ..domain.exceptions import FileProcessingError, SecurityInfoExtractionError
from ..domain.value_objects import (
    parse_company,
    parse_currency,
)
from ..infrastructure.isin_country import isin_to_country
from ..infrastructure.logging_config import create_module_logger


class IBCsvSection(Enum):
    """Enum to track current section being processed in IB CSV file."""

    UNKNOWN = "unknown"
    FINANCIAL_INSTRUMENT = "financial_instrument"
    TRADES = "trades"
    DIVIDENDS = "dividends"
    WITHHOLDING_TAX = "withholding_tax"
    OTHER = "other"


@dataclass
class IBCsvData:
    """Container for all raw data extracted from IB CSV file."""

    security_info: dict[str, dict[str, str]]
    raw_trade_data: list[dict[str, str]]
    raw_dividend_data: list[dict[str, str]]
    raw_withholding_tax_data: list[dict[str, str]]
    metadata: dict[str, int]  # Processing statistics


class BaseSectionContext:
    """Base class for CSV section processing contexts."""

    def __init__(self):
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
        super().__init__()
        self.security_info = security_info
        self.security_processed_count = 0

    def process_header(self, row: list[str]) -> None:
        """Process Financial Instrument Information header."""
        if len(row) >= 7 and row[1] == "Header" and row[3] == "Symbol" and row[6] == "Security ID":
            self.headers_found = True
            self.logger.debug("Found Financial Instrument Information header")
        else:
            raise FileProcessingError(
                f"Invalid 'Financial Instrument Information' header format: {row}"
            )

    def process_data_row(self, row: list[str]) -> None:
        """Process security info data row."""
        if not self.can_process_row(row):
            return

        if len(row) >= 7 and row[1] == "Data" and row[2] == "Stocks":
            symbol = row[3] if len(row) > 3 else ""
            isin = row[6] if len(row) > 6 else ""

            if symbol and isin:
                try:
                    country = isin_to_country(isin)
                    self.security_info[symbol] = {"isin": isin, "country": country}
                    self.security_processed_count += 1
                    self.processed_count += 1
                    self.logger.debug(f"Extracted security info for {symbol}: {isin} ({country})")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to extract country for {symbol} with ISIN {isin}: {e}"
                    )
                    self.security_info[symbol] = {"isin": isin, "country": "Unknown"}
                    self.processed_count += 1

    def validate_header(self, row: list[str]) -> bool:
        """Validate Financial Instrument Information header."""
        return len(row) >= 2 and row[0] == "Financial Instrument Information" and row[1] == "Header"


class TradesContext(BaseSectionContext):
    """Context for processing Trades section."""

    def __init__(self, raw_trade_data: list[dict[str, str]], require_trades_section: bool = True):
        super().__init__()
        self.raw_trade_data = raw_trade_data
        self.require_trades_section = require_trades_section
        self.trades_headers = None
        self.trades_col_mapping = None
        self.skipped_trades = 0

    def process_header(self, row: list[str]) -> None:
        """Process Trades section header."""
        if len(row) >= 2 and row[1] == "Header":
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
                self.logger.debug(f"Column mapping: {self.trades_col_mapping}")
            except ValueError as e:
                if self.require_trades_section:
                    raise FileProcessingError(
                        f"Missing required column in Trades section: {e}"
                    ) from e
                else:
                    # If trades section is not required, just skip it
                    self.logger.debug(f"Skipping Trades section due to missing columns: {e}")
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

        if len(row) > 2 and (row[2] != "Order" or row[3] != "Stocks"):
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

        if self.processed_count <= 5 or self.processed_count % 100 == 0:
            self.logger.debug(
                f"Collected trade {self.processed_count}: {trade_row['symbol']} {trade_row['currency']} {trade_row['quantity']} @ {trade_row['price']}"
            )

    def validate_header(self, row: list[str]) -> bool:
        """Validate Trades header."""
        return len(row) >= 2 and row[0] == "Trades" and row[1] == "Header"


class DividendsContext(BaseSectionContext):
    """Context for processing Dividends section."""

    def __init__(self, raw_dividend_data: list[dict[str, str]]):
        super().__init__()
        self.raw_dividend_data = raw_dividend_data
        self.dividends_headers = None
        self.dividends_col_mapping = None

    def process_header(self, row: list[str]) -> None:
        """Process Dividends section header."""
        if len(row) >= 2 and row[1] == "Header":
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
                self.logger.debug(f"Dividend column mapping: {self.dividends_col_mapping}")
            except ValueError as e:
                self.logger.debug(f"Skipping Dividends section due to missing columns: {e}")
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

            if self.processed_count <= 5:
                self.logger.debug(
                    f"Collected dividend {self.processed_count}: {dividend_row['description']} {dividend_row['currency']} {dividend_row['amount']}"
                )

    def validate_header(self, row: list[str]) -> bool:
        """Validate Dividends header."""
        return len(row) >= 2 and row[0] == "Dividends" and row[1] == "Header"


class WithholdingTaxContext(BaseSectionContext):
    """Context for processing Withholding Tax section."""

    def __init__(self, raw_withholding_tax_data: list[dict[str, str]]):
        super().__init__()
        self.raw_withholding_tax_data = raw_withholding_tax_data
        self.withholding_tax_headers = None
        self.withholding_tax_col_mapping = None

    def process_header(self, row: list[str]) -> None:
        """Process Withholding Tax section header."""
        if len(row) >= 2 and row[1] == "Header":
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
                self.logger.debug(f"Skipping Withholding Tax section due to missing columns: {e}")
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

            if self.processed_count <= 5:
                self.logger.debug(
                    f"Collected withholding tax {self.processed_count}: {tax_row['description']} {tax_row['currency']} {tax_row['amount']}"
                )

    def validate_header(self, row: list[str]) -> bool:
        """Validate Withholding Tax header."""
        return len(row) >= 2 and row[0] == "Withholding Tax" and row[1] == "Header"


class IBCsvStateMachine:
    """State machine for processing IB CSV files."""

    def __init__(self, require_trades_section: bool = True):
        self.logger = create_module_logger(__name__)
        self.current_section = IBCsvSection.UNKNOWN
        self.require_trades_section = require_trades_section

        # Initialize data containers
        self.security_info: dict[str, dict[str, str]] = {}
        self.raw_trade_data: list[dict[str, str]] = []
        self.raw_dividend_data: list[dict[str, str]] = []
        self.raw_withholding_tax_data: list[dict[str, str]] = []

        # Initialize contexts
        self.financial_context = FinancialInstrumentContext(self.security_info)
        self.trades_context = TradesContext(self.raw_trade_data, require_trades_section)
        self.dividends_context = DividendsContext(self.raw_dividend_data)
        self.withholding_tax_context = WithholdingTaxContext(self.raw_withholding_tax_data)

        # Tracking
        self.found_financial_instrument_header = False

    def process_row(self, row: list[str]) -> None:
        """Process a single CSV row using the state machine."""
        if len(row) < 2:
            return

        # Check for section transitions
        if self._detect_section_transition(row):
            return

        # Process row based on current section
        if self.current_section == IBCsvSection.FINANCIAL_INSTRUMENT:
            self._process_financial_instrument_row(row)
        elif self.current_section == IBCsvSection.TRADES:
            self._process_trades_row(row)
        elif self.current_section == IBCsvSection.DIVIDENDS:
            self._process_dividends_row(row)
        elif self.current_section == IBCsvSection.WITHHOLDING_TAX:
            self._process_withholding_tax_row(row)
        # OTHER sections are ignored

    def _detect_section_transition(self, row: list[str]) -> bool:
        """Detect if this row represents a section transition."""
        # Only treat as section transition if it's a header row
        if row[0] == "Financial Instrument Information" and len(row) >= 2 and row[1] == "Header":
            self._transition_to_financial_instruments(row)
            return True
        elif row[0] == "Trades" and len(row) >= 2 and row[1] == "Header":
            self._transition_to_trades(row)
            return True
        elif row[0] == "Dividends" and len(row) >= 2 and row[1] == "Header":
            self._transition_to_dividends(row)
            return True
        elif row[0] == "Withholding Tax" and len(row) >= 2 and row[1] == "Header":
            self._transition_to_withholding_tax(row)
            return True
        return False

    def _transition_to_financial_instruments(self, row: list[str]) -> None:
        """Transition to Financial Instrument section."""
        self.current_section = IBCsvSection.FINANCIAL_INSTRUMENT
        if len(row) >= 2 and row[1] == "Header":
            try:
                self.financial_context.process_header(row)
                self.found_financial_instrument_header = True
            except Exception as e:
                self.logger.warning(
                    f"Failed to process financial instrument header: {e}, row: {row}"
                )
                # Continue processing even if header validation fails

    def _transition_to_trades(self, row: list[str]) -> None:
        """Transition to Trades section."""
        self.current_section = IBCsvSection.TRADES
        if len(row) >= 2 and row[1] == "Header":
            self.trades_context.process_header(row)

    def _transition_to_dividends(self, row: list[str]) -> None:
        """Transition to Dividends section."""
        self.current_section = IBCsvSection.DIVIDENDS
        if len(row) >= 2 and row[1] == "Header":
            self.dividends_context.process_header(row)

    def _transition_to_withholding_tax(self, row: list[str]) -> None:
        """Transition to Withholding Tax section."""
        self.current_section = IBCsvSection.WITHHOLDING_TAX
        if len(row) >= 2 and row[1] == "Header":
            self.withholding_tax_context.process_header(row)

    def _process_financial_instrument_row(self, row: list[str]) -> None:
        """Process row in Financial Instrument section."""
        if len(row) >= 2 and row[1] == "Data":
            self.financial_context.process_data_row(row)

    def _process_trades_row(self, row: list[str]) -> None:
        """Process row in Trades section."""
        if len(row) >= 2 and row[1] == "Data":
            self.trades_context.process_data_row(row)

    def _process_dividends_row(self, row: list[str]) -> None:
        """Process row in Dividends section."""
        if len(row) >= 2 and row[1] == "Data":
            self.dividends_context.process_data_row(row)

    def _process_withholding_tax_row(self, row: list[str]) -> None:
        """Process row in Withholding Tax section."""
        if len(row) >= 2 and row[1] == "Data":
            self.withholding_tax_context.process_data_row(row)

    def finalize(self) -> IBCsvData:
        """Finalize processing and return collected data."""
        # Validation
        if not self.found_financial_instrument_header:
            raise FileProcessingError("Missing 'Financial Instrument Information' header in CSV")

        if self.require_trades_section and not self.trades_context.headers_found:
            raise FileProcessingError("No Trades section found in the IB export file")

        metadata = {
            "processed_trades": self.trades_context.processed_count,
            "skipped_trades": self.trades_context.skipped_trades,
            "processed_dividends": self.dividends_context.processed_count,
            "processed_withholding_taxes": self.withholding_tax_context.processed_count,
            "security_processed_count": self.financial_context.security_processed_count,
        }

        self.logger.info(
            f"Extracted security data for {len(self.security_info)} symbols ({self.financial_context.security_processed_count} with country data)"
        )
        self.logger.info(
            f"Collected {self.trades_context.processed_count} trades, {self.dividends_context.processed_count} dividends and {self.withholding_tax_context.processed_count} withholding taxes"
        )
        if self.trades_context.skipped_trades > 0:
            self.logger.warning(f"Skipped {self.trades_context.skipped_trades} invalid trades")

        return IBCsvData(
            security_info=self.security_info,
            raw_trade_data=self.raw_trade_data,
            raw_dividend_data=self.raw_dividend_data,
            raw_withholding_tax_data=self.raw_withholding_tax_data,
            metadata=metadata,
        )


def _extract_csv_data(path: str | Path, require_trades_section: bool = True) -> IBCsvData:
    """
    Collect all raw data from IB export CSV file using a state machine approach.

    This function reads the file once and extracts security information,
    raw trade data, and dividend data for deferred processing using a proper
    state machine pattern.

    Args:
        path: Path to the raw IB export CSV file
        require_trades_section: If True, requires Trades section to be present (default True)

    Returns:
        IBCsvData container with all collected information
    """
    logger = create_module_logger(__name__)

    try:
        # Initialize state machine
        state_machine = IBCsvStateMachine(require_trades_section)

        # Process CSV file row by row using state machine
        with open(path, encoding="utf-8") as read_obj:
            csv_reader = csv.reader(read_obj)

            for row in csv_reader:
                state_machine.process_row(row)

        # Finalize processing and return results
        return state_machine.finalize()

    except csv.Error as e:
        raise FileProcessingError(f"CSV parsing error: {e}") from e
    except UnicodeDecodeError as e:
        raise FileProcessingError(f"File encoding error: {e}") from e
    except OSError as e:
        raise FileProcessingError(f"File access error: {e}") from e
    except FileProcessingError:
        raise
    except Exception as e:
        raise SecurityInfoExtractionError(f"Unexpected error while parsing IB file: {e}") from e


def _process_trades(csv_data: IBCsvData) -> TradeCyclePerCompany:
    """
    Process raw trade data using complete security information.

    This function converts the collected raw trade data into domain objects
    with full security context (ISIN, country) available.

    Args:
        csv_data: IBCsvData container with security_info and raw_trade_data

    Returns:
        TradeCyclePerCompany with fully processed domain objects
    """
    logger = create_module_logger(__name__)
    trade_cycles_per_company: TradeCyclePerCompany = {}

    for trade_row in csv_data.raw_trade_data:
        symbol = trade_row["symbol"]
        currency_str = trade_row["currency"]
        datetime_val = trade_row["datetime"]
        quantity = trade_row["quantity"]
        price = trade_row["price"]
        fee = trade_row["fee"]

        try:
            # Get security info now that it's fully available
            symbol_info = csv_data.security_info.get(symbol, {})
            isin = symbol_info.get("isin", "")
            country = symbol_info.get("country", "Unknown")

            company = parse_company(symbol, isin, country)
            currency = parse_currency(currency_str)

            currency_company: CurrencyCompany = CurrencyCompany(currency=currency, company=company)
            if currency_company in trade_cycles_per_company:
                trade_cycle: TradeCycle = trade_cycles_per_company[currency_company]
            else:
                trade_cycle: TradeCycle = TradeCycle()
                trade_cycles_per_company[currency_company] = trade_cycle

            trade_action = TradeAction(company, datetime_val, currency, quantity, price, fee)
            quantitated_trade_actions: QuantitatedTradeActions = trade_cycle.get(
                trade_action.trade_type
            )
            quantitated_trade_actions.append(
                QuantitatedTradeAction(trade_action.quantity, trade_action)
            )

        except Exception as e:
            logger.warning(f"Failed to process trade for {symbol}: {e}")
            continue

    logger.info(
        f"Processed {len(csv_data.raw_trade_data)} trades for {len(trade_cycles_per_company)} currency-company pairs"
    )
    return trade_cycles_per_company


def _process_dividends(csv_data: IBCsvData) -> DividendIncomePerCompany:
    """
    Process raw dividend data using complete security information.

    This function aggregates dividend amounts per security for capital investment
    income reporting, using the complete security context (ISIN, country).

    Args:
        csv_data: IBCsvData container with security_info and raw_dividend_data

    Returns:
        DividendIncomePerCompany mapping symbol to aggregated dividend data
    """
    logger = create_module_logger(__name__)
    dividend_income_per_company: DividendIncomePerCompany = {}

    # Temporary aggregation structure
    aggregation: dict[
        str, dict[str, Decimal]
    ] = {}  # symbol -> {gross_amount, total_taxes, currency}

    for dividend_row in csv_data.raw_dividend_data:
        description = dividend_row["description"]
        currency_str = dividend_row["currency"]
        amount_str = dividend_row["amount"]

        try:
            # Extract symbol from description (IB format: "SYMBOL - Description")
            if " - " in description:
                symbol = description.split(" - ")[0].strip()
            else:
                # Fallback: try to extract what looks like a ticker symbol
                symbol_match = re.search(r"([A-Z]{1,5})", description)
                symbol = symbol_match.group(1) if symbol_match else description.strip()

            if not symbol:
                logger.warning(f"Could not extract symbol from dividend description: {description}")
                continue

            # Get security info now that it's fully available
            symbol_info = csv_data.security_info.get(symbol, {})
            if not symbol_info:
                logger.warning(f"No security info found for dividend symbol: {symbol}")
                continue

            # Parse amounts (no tax in dividend section)
            amount = Decimal(amount_str.replace(",", "")) if amount_str else Decimal("0")

            # Aggregate by symbol and currency
            key = f"{symbol}_{currency_str}"
            if key not in aggregation:
                aggregation[key] = {
                    "gross_amount": Decimal("0"),
                    "total_taxes": Decimal("0"),
                    "currency": currency_str,
                }

            aggregation[key]["gross_amount"] += amount

        except Exception as e:
            logger.warning(f"Failed to process dividend for {description}: {e}")
            continue

    # Process withholding tax data and add taxes to aggregation
    for tax_row in csv_data.raw_withholding_tax_data:
        description = tax_row["description"]
        currency_str = tax_row["currency"]
        tax_amount_str = tax_row["amount"]

        try:
            # Extract ISIN from withholding tax description (format: "SYMBOL(ISIN) Description - Tax")
            isin_match = re.search(r"\(([A-Z0-9]+)\)", description)
            if not isin_match:
                logger.warning(
                    f"Could not extract ISIN from withholding tax description: {description}"
                )
                continue

            isin = isin_match.group(1)

            # Find symbol by ISIN
            symbol = None
            for ticker_symbol, symbol_info in csv_data.security_info.items():
                if symbol_info.get("isin") == isin:
                    symbol = ticker_symbol
                    break

            if not symbol:
                logger.warning(
                    f"Could not find symbol for ISIN {isin} in withholding tax: {description}"
                )
                continue

            # Parse tax amount (withholding tax amounts are negative)
            tax_amount = (
                Decimal(tax_amount_str.replace(",", "")) if tax_amount_str else Decimal("0")
            )
            # Use absolute value since we track positive tax amounts
            tax_amount = abs(tax_amount)

            # Aggregate by symbol and currency
            key = f"{symbol}_{currency_str}"
            if key not in aggregation:
                aggregation[key] = {
                    "gross_amount": Decimal("0"),
                    "total_taxes": Decimal("0"),
                    "currency": currency_str,
                }

            aggregation[key]["total_taxes"] += tax_amount

        except Exception as e:
            logger.warning(f"Failed to process withholding tax for {description}: {e}")
            continue

    # Convert aggregation to domain objects
    for key, data in aggregation.items():
        try:
            symbol = key.split("_")[0]
            currency_str = data["currency"]

            symbol_info = csv_data.security_info.get(symbol, {})
            isin = symbol_info.get("isin", "")
            country = symbol_info.get("country", "Unknown")

            if not isin:
                logger.warning(f"No ISIN found for dividend symbol: {symbol}")
                continue

            currency = parse_currency(currency_str)

            dividend_income = DividendIncomePerSecurity(
                symbol=symbol,
                isin=isin,
                country=country,
                gross_amount=data["gross_amount"],
                total_taxes=data["total_taxes"],
                currency=currency,
            )

            dividend_income.validate()
            dividend_income_per_company[symbol] = dividend_income

        except Exception as e:
            logger.warning(f"Failed to create dividend income object for {key}: {e}")
            continue

    logger.info(
        f"Processed {len(csv_data.raw_dividend_data)} dividend entries into {len(dividend_income_per_company)} securities"
    )
    return dividend_income_per_company


def parse_ib_export(path: str | Path) -> TradeCyclePerCompany:
    """
    Parse raw Interactive Brokers export CSV file with ISIN and country extraction.

    This function processes raw IB exports directly, extracting both trade data
    and financial instrument information to populate country of issuance data.

    Args:
        path: Path to the raw IB export CSV file

    Returns:
        TradeCyclePerCompany with enriched Company objects containing ISIN and country data
    """
    logger = create_module_logger(__name__)

    try:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        if not validated_path.is_file():
            raise FileProcessingError(f"Path is not a file: {validated_path}")
        if validated_path.suffix.lower() != ".csv":
            raise FileProcessingError(f"File must have .csv extension: {validated_path}")
    except Exception as e:
        raise FileProcessingError(f"Invalid source file: {e}") from e

    logger.info(f"Processing raw IB export: {validated_path.name}")

    try:
        csv_data = _extract_csv_data(validated_path)
        return _process_trades(csv_data)
    except Exception as e:
        raise FileProcessingError(f"Failed to parse raw IB export: {e}") from e


def parse_dividend_income(path: str | Path) -> DividendIncomePerCompany:
    """
    Extract dividend income data from IB export CSV file for capital investment income reporting.

    This function processes dividend entries and aggregates them per security,
    using financial instrument information for country and ISIN data.

    Args:
        path: Path to the raw IB export CSV file

    Returns:
        DividendIncomePerCompany mapping symbol to aggregated dividend income data

    Raises:
        FileProcessingError: For file-related errors
        SecurityInfoExtractionError: For data processing errors
    """
    logger = create_module_logger(__name__)

    try:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        if not validated_path.is_file():
            raise FileProcessingError(f"Path is not a file: {validated_path}")
        if validated_path.suffix.lower() != ".csv":
            raise FileProcessingError(f"File must have .csv extension: {validated_path}")
    except Exception as e:
        raise FileProcessingError(f"Invalid source file: {e}") from e

    logger.info(f"Extracting dividend income from: {validated_path.name}")

    try:
        csv_data = _extract_csv_data(validated_path)
        return _process_dividends(csv_data)
    except Exception as e:
        raise FileProcessingError(f"Failed to extract dividend income: {e}") from e


def parse_ib_export_all(path: str | Path) -> IBExportData:
    """
    Extract all data types from Interactive Brokers export CSV in single pass.

    This function processes raw Interactive Brokers CSV files to extract comprehensive
    trading data including trades, dividends, security information, and tax data.
    Uses a single-pass state machine approach for efficiency and data consistency.

    Args:
        path: Path to the raw Interactive Brokers export CSV file

    Returns:
        IBExportData containing both trade cycles and dividend income data

    Raises:
        FileProcessingError: For file-related errors
        SecurityInfoExtractionError: For data processing errors
    """
    logger = create_module_logger(__name__)

    try:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        if not validated_path.is_file():
            raise FileProcessingError(f"Path is not a file: {validated_path}")
        if validated_path.suffix.lower() != ".csv":
            raise FileProcessingError(f"File must have .csv extension: {validated_path}")
    except Exception as e:
        raise FileProcessingError(f"Invalid source file: {e}") from e

    logger.info(f"Processing complete IB export: {validated_path.name}")

    try:
        csv_data = _extract_csv_data(validated_path)
        trade_cycles = _process_trades(csv_data)
        dividend_income = _process_dividends(csv_data)

        return IBExportData(trade_cycles=trade_cycles, dividend_income=dividend_income)
    except Exception as e:
        raise FileProcessingError(f"Failed to parse complete IB export: {e}") from e
