import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Union

from ..domain.collections import QuantitatedTradeActions, TradeCyclePerCompany, DividendIncomePerCompany
from ..domain.entities import (
    CurrencyCompany,
    QuantitatedTradeAction,
    TradeAction,
    TradeCycle,
    DividendIncomePerSecurity,
)
from ..domain.exceptions import FileProcessingError, SecurityInfoExtractionError
from enum import Enum
from ..domain.value_objects import get_company, get_currency
from ..infrastructure.isin_country import isin_to_country
from ..infrastructure.logging_config import get_logger


class IBCsvSection(Enum):
    """Enum to track current section being processed in IB CSV file."""
    UNKNOWN = "unknown"
    FINANCIAL_INSTRUMENT = "financial_instrument"
    TRADES = "trades"
    DIVIDENDS = "dividends"
    OTHER = "other"


@dataclass
class IBCsvData:
    """Container for all raw data extracted from IB CSV file."""
    security_info: Dict[str, Dict[str, str]]
    raw_trade_data: List[Dict[str, str]]
    raw_dividend_data: List[Dict[str, str]]
    metadata: Dict[str, int]  # Processing statistics


def _collect_ib_csv_data(path: Union[str, Path], require_trades_section: bool = True) -> IBCsvData:
    """
    Collect all raw data from IB export CSV file in a single pass.

    This function reads the file once and extracts security information,
    raw trade data, and dividend data for deferred processing.

    Args:
        path: Path to the raw IB export CSV file
        require_trades_section: If True, requires Trades section to be present (default True)

    Returns:
        IBCsvData container with all collected information
    """
    logger = get_logger(__name__)
    security_info: Dict[str, Dict[str, str]] = {}
    raw_trade_data: List[Dict[str, str]] = []
    raw_dividend_data: List[Dict[str, str]] = []

    # State tracking
    current_section = IBCsvSection.UNKNOWN
    trades_headers = None
    trades_col_mapping = None
    dividends_headers = None
    dividends_col_mapping = None
    found_financial_instrument_header = False

    processed_trades = 0
    skipped_trades = 0
    processed_dividends = 0
    security_processed_count = 0

    try:
        with open(path, "r", encoding="utf-8") as read_obj:
            csv_reader = csv.reader(read_obj)

            for row in csv_reader:
                if len(row) < 2:
                    continue

                # Detect section changes
                if row[0] == "Financial Instrument Information":
                    current_section = IBCsvSection.FINANCIAL_INSTRUMENT

                    # Check for header
                    if (row[1] == "Header" and len(row) >= 7 and
                        row[3] == "Symbol" and row[6] == "Security ID"):
                        found_financial_instrument_header = True
                        logger.debug("Found Financial Instrument Information header")
                    elif row[1] == "Data" and len(row) >= 7 and row[2] == "Stocks":
                        if not found_financial_instrument_header:
                            raise FileProcessingError("Missing 'Financial Instrument Information' header in CSV")

                        # Process security info data immediately (independent data)
                        symbol = row[3] if len(row) > 3 else ""
                        isin = row[6] if len(row) > 6 else ""

                        if symbol and isin:
                            try:
                                country = isin_to_country(isin)
                                security_info[symbol] = {"isin": isin, "country": country}
                                security_processed_count += 1
                                logger.debug(f"Extracted security info for {symbol}: {isin} ({country})")
                            except Exception as e:
                                logger.warning(f"Failed to extract country for {symbol} with ISIN {isin}: {e}")
                                security_info[symbol] = {"isin": isin, "country": "Unknown"}
                    continue

                elif row[0] == "Trades":
                    current_section = IBCsvSection.TRADES

                    if row[1] == "Header":
                        trades_headers = row
                        logger.debug("Found Trades section header")

                        # Create column mapping
                        try:
                            # Handle different fee column names
                            fee_column = None
                            if "Comm/Fee" in trades_headers:
                                fee_column = trades_headers.index("Comm/Fee")
                            elif "Comm in EUR" in trades_headers:
                                fee_column = trades_headers.index("Comm in EUR")
                            elif "Commission" in trades_headers:
                                fee_column = trades_headers.index("Commission")

                            trades_col_mapping = {
                                "symbol": trades_headers.index("Symbol"),
                                "currency": trades_headers.index("Currency"),
                                "datetime": trades_headers.index("Date/Time"),
                                "quantity": trades_headers.index("Quantity"),
                                "price": trades_headers.index("T. Price"),
                                "fee": fee_column,
                            }
                            logger.debug(f"Column mapping: {trades_col_mapping}")
                        except ValueError as e:
                            if require_trades_section:
                                raise FileProcessingError(f"Missing required column in Trades section: {e}") from e
                            else:
                                # If trades section is not required, just skip it
                                logger.debug(f"Skipping Trades section due to missing columns: {e}")
                                trades_headers = None
                                trades_col_mapping = None
                    elif row[1] == "Data" and trades_col_mapping:
                        # Collect raw trade data for deferred processing
                        if len(row) < len(trades_headers):
                            skipped_trades += 1
                            continue

                        if len(row) > 2 and (row[2] != "Order" or row[3] != "Stocks"):
                            skipped_trades += 1
                            continue

                        # Extract trade data as dictionary for deferred processing
                        fee_value = ""
                        if trades_col_mapping["fee"] is not None:
                            fee_value = row[trades_col_mapping["fee"]] if len(row) > trades_col_mapping["fee"] else ""

                        trade_row = {
                            "symbol": row[trades_col_mapping["symbol"]] if len(row) > trades_col_mapping["symbol"] else "",
                            "currency": row[trades_col_mapping["currency"]] if len(row) > trades_col_mapping["currency"] else "",
                            "datetime": row[trades_col_mapping["datetime"]] if len(row) > trades_col_mapping["datetime"] else "",
                            "quantity": row[trades_col_mapping["quantity"]] if len(row) > trades_col_mapping["quantity"] else "",
                            "price": row[trades_col_mapping["price"]] if len(row) > trades_col_mapping["price"] else "",
                            "fee": fee_value,
                        }

                        if not trade_row["symbol"] or not trade_row["datetime"] or trade_row["datetime"].strip() == "":
                            skipped_trades += 1
                            continue

                        raw_trade_data.append(trade_row)
                        processed_trades += 1

                        if processed_trades <= 5 or processed_trades % 100 == 0:
                            logger.debug(f"Collected trade {processed_trades}: {trade_row['symbol']} {trade_row['currency']} {trade_row['quantity']} @ {trade_row['price']}")
                    continue

                elif row[0] == "Dividends":
                    current_section = IBCsvSection.DIVIDENDS

                    if row[1] == "Header":
                        dividends_headers = row
                        logger.debug("Found Dividends section header")

                        # Create column mapping
                        try:
                            dividends_col_mapping = {
                                "currency": dividends_headers.index("Currency"),
                                "date": dividends_headers.index("Date"),
                                "description": dividends_headers.index("Description"),
                                "amount": dividends_headers.index("Amount"),
                            }
                            # Tax column is optional
                            try:
                                dividends_col_mapping["tax"] = dividends_headers.index("Tax")
                            except ValueError:
                                dividends_col_mapping["tax"] = None
                            logger.debug(f"Dividend column mapping: {dividends_col_mapping}")
                        except ValueError as e:
                            logger.debug(f"Skipping Dividends section due to missing columns: {e}")
                            dividends_headers = None
                            dividends_col_mapping = None
                    elif row[1] == "Data" and dividends_col_mapping:
                        # Collect raw dividend data for deferred processing
                        dividend_row = {
                            "currency": row[dividends_col_mapping["currency"]] if len(row) > dividends_col_mapping["currency"] else "",
                            "date": row[dividends_col_mapping["date"]] if len(row) > dividends_col_mapping["date"] else "",
                            "description": row[dividends_col_mapping["description"]] if len(row) > dividends_col_mapping["description"] else "",
                            "amount": row[dividends_col_mapping["amount"]] if len(row) > dividends_col_mapping["amount"] else "",
                            "tax": row[dividends_col_mapping["tax"]] if dividends_col_mapping["tax"] is not None and len(row) > dividends_col_mapping["tax"] else "0",
                        }

                        if dividend_row["description"] and dividend_row["amount"]:
                            raw_dividend_data.append(dividend_row)
                            processed_dividends += 1

                            if processed_dividends <= 5:
                                logger.debug(f"Collected dividend {processed_dividends}: {dividend_row['description']} {dividend_row['currency']} {dividend_row['amount']}")
                    continue
                else:
                    # Other sections - skip
                    continue

        # Validation
        if not found_financial_instrument_header:
            raise FileProcessingError("Missing 'Financial Instrument Information' header in CSV")

        if require_trades_section and not trades_headers:
            raise FileProcessingError("No Trades section found in the IB export file")

        metadata = {
            "processed_trades": processed_trades,
            "skipped_trades": skipped_trades,
            "processed_dividends": processed_dividends,
            "security_processed_count": security_processed_count,
        }

        logger.info(f"Extracted security data for {len(security_info)} symbols ({security_processed_count} with country data)")
        logger.info(f"Collected {processed_trades} trades and {processed_dividends} dividends")
        if skipped_trades > 0:
            logger.warning(f"Skipped {skipped_trades} invalid trades")

        return IBCsvData(
            security_info=security_info,
            raw_trade_data=raw_trade_data,
            raw_dividend_data=raw_dividend_data,
            metadata=metadata
        )

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


def _process_trades_with_securities(csv_data: IBCsvData) -> TradeCyclePerCompany:
    """
    Process raw trade data using complete security information.

    This function converts the collected raw trade data into domain objects
    with full security context (ISIN, country) available.

    Args:
        csv_data: IBCsvData container with security_info and raw_trade_data

    Returns:
        TradeCyclePerCompany with fully processed domain objects
    """
    logger = get_logger(__name__)
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

            company = get_company(symbol, isin, country)
            currency = get_currency(currency_str)

            currency_company: CurrencyCompany = CurrencyCompany(
                currency=currency, company=company
            )
            if currency_company in trade_cycles_per_company:
                trade_cycle: TradeCycle = trade_cycles_per_company[currency_company]
            else:
                trade_cycle: TradeCycle = TradeCycle()
                trade_cycles_per_company[currency_company] = trade_cycle

            trade_action = TradeAction(
                company, datetime_val, currency, quantity, price, fee
            )
            quantitated_trade_actions: QuantitatedTradeActions = trade_cycle.get(
                trade_action.trade_type
            )
            quantitated_trade_actions.append(
                QuantitatedTradeAction(trade_action.quantity, trade_action)
            )

        except Exception as e:
            logger.warning(f"Failed to process trade for {symbol}: {e}")
            continue

    logger.info(f"Processed {len(csv_data.raw_trade_data)} trades for {len(trade_cycles_per_company)} currency-company pairs")
    return trade_cycles_per_company


def _process_dividends_with_securities(csv_data: IBCsvData) -> DividendIncomePerCompany:
    """
    Process raw dividend data using complete security information.

    This function aggregates dividend amounts per security for capital investment
    income reporting, using the complete security context (ISIN, country).

    Args:
        csv_data: IBCsvData container with security_info and raw_dividend_data

    Returns:
        DividendIncomePerCompany mapping symbol to aggregated dividend data
    """
    logger = get_logger(__name__)
    dividend_income_per_company: DividendIncomePerCompany = {}

    # Temporary aggregation structure
    aggregation: Dict[str, Dict[str, Decimal]] = {}  # symbol -> {gross_amount, total_taxes, currency}

    for dividend_row in csv_data.raw_dividend_data:
        description = dividend_row["description"]
        currency_str = dividend_row["currency"]
        amount_str = dividend_row["amount"]
        tax_str = dividend_row["tax"]

        try:
            # Extract symbol from description (IB format: "SYMBOL - Description")
            if " - " in description:
                symbol = description.split(" - ")[0].strip()
            else:
                # Fallback: try to extract what looks like a ticker symbol
                symbol_match = re.search(r'([A-Z]{1,5})', description)
                symbol = symbol_match.group(1) if symbol_match else description.strip()

            if not symbol:
                logger.warning(f"Could not extract symbol from dividend description: {description}")
                continue

            # Get security info now that it's fully available
            symbol_info = csv_data.security_info.get(symbol, {})
            if not symbol_info:
                logger.warning(f"No security info found for dividend symbol: {symbol}")
                continue

            # Parse amounts
            amount = Decimal(amount_str.replace(",", "")) if amount_str else Decimal('0')
            tax = Decimal(tax_str.replace(",", "")) if tax_str and tax_str != "0" else Decimal('0')

            # Aggregate by symbol and currency
            key = f"{symbol}_{currency_str}"
            if key not in aggregation:
                aggregation[key] = {
                    "gross_amount": Decimal('0'),
                    "total_taxes": Decimal('0'),
                    "currency": currency_str
                }

            aggregation[key]["gross_amount"] += amount
            aggregation[key]["total_taxes"] += tax

        except Exception as e:
            logger.warning(f"Failed to process dividend for {description}: {e}")
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

            currency = get_currency(currency_str)

            dividend_income = DividendIncomePerSecurity(
                symbol=symbol,
                isin=isin,
                country=country,
                gross_amount=data["gross_amount"],
                total_taxes=data["total_taxes"],
                currency=currency
            )

            dividend_income.validate()
            dividend_income_per_company[symbol] = dividend_income

        except Exception as e:
            logger.warning(f"Failed to create dividend income object for {key}: {e}")
            continue

    logger.info(f"Processed {len(csv_data.raw_dividend_data)} dividend entries into {len(dividend_income_per_company)} securities")
    return dividend_income_per_company


def extract_security_info(path: Union[str, Path]) -> Dict[str, Dict[str, str]]:
    """
    Parses the "Financial Instrument Information" sections to build a mapping
    of ticker symbols to their ISIN codes and countries of issuance.

    Args:
        path: Path to the raw IB export CSV file

    Returns:
        Dictionary mapping symbol -> {'isin': str, 'country': str}
    """
    logger = get_logger(__name__)

    try:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        if not validated_path.is_file():
            raise FileProcessingError(f"Path is not a file: {validated_path}")
        if validated_path.suffix.lower() != '.csv':
            raise FileProcessingError(f"File must have .csv extension: {validated_path}")
    except Exception as e:
        raise FileProcessingError(f"Invalid source file: {e}") from e

    logger.info(f"Extracting security info from: {validated_path.name}")

    try:
        csv_data = _collect_ib_csv_data(validated_path, require_trades_section=False)
        return csv_data.security_info
    except FileProcessingError:
        # Allow FileProcessingError to bubble up unchanged for test compatibility
        raise
    except Exception as e:
        raise SecurityInfoExtractionError(f"Failed to extract security info: {e}") from e


def parse_raw_ib_export(path: Union[str, Path]) -> TradeCyclePerCompany:
    """
    Parse raw Interactive Brokers export CSV file with ISIN and country extraction.

    This function processes raw IB exports directly, extracting both trade data
    and financial instrument information to populate country of issuance data.

    Args:
        path: Path to the raw IB export CSV file

    Returns:
        TradeCyclePerCompany with enriched Company objects containing ISIN and country data
    """
    logger = get_logger(__name__)

    try:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        if not validated_path.is_file():
            raise FileProcessingError(f"Path is not a file: {validated_path}")
        if validated_path.suffix.lower() != '.csv':
            raise FileProcessingError(f"File must have .csv extension: {validated_path}")
    except Exception as e:
        raise FileProcessingError(f"Invalid source file: {e}") from e

    logger.info(f"Processing raw IB export: {validated_path.name}")

    try:
        csv_data = _collect_ib_csv_data(validated_path)
        return _process_trades_with_securities(csv_data)
    except Exception as e:
        raise FileProcessingError(f"Failed to parse raw IB export: {e}") from e


def extract_dividend_income(path: Union[str, Path]) -> DividendIncomePerCompany:
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
    logger = get_logger(__name__)

    try:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        if not validated_path.is_file():
            raise FileProcessingError(f"Path is not a file: {validated_path}")
        if validated_path.suffix.lower() != '.csv':
            raise FileProcessingError(f"File must have .csv extension: {validated_path}")
    except Exception as e:
        raise FileProcessingError(f"Invalid source file: {e}") from e

    logger.info(f"Extracting dividend income from: {validated_path.name}")

    try:
        csv_data = _collect_ib_csv_data(validated_path)
        return _process_dividends_with_securities(csv_data)
    except Exception as e:
        raise FileProcessingError(f"Failed to extract dividend income: {e}") from e


