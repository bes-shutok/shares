import csv
from pathlib import Path
from typing import Dict, Union

from ..domain.collections import QuantitatedTradeActions, TradeCyclePerCompany
from ..domain.entities import (
    CurrencyCompany,
    QuantitatedTradeAction,
    TradeAction,
    TradeCycle,
)
from ..domain.exceptions import FileProcessingError, SecurityInfoExtractionError
from ..domain.value_objects import get_company, get_currency
from ..infrastructure.isin_country import isin_to_country
from ..infrastructure.logging_config import get_logger


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
    security_info: Dict[str, Dict[str, str]] = {}

    try:
        with open(path, "r", encoding="utf-8") as read_obj:
            csv_reader = csv.reader(read_obj)

            for row in csv_reader:
                if (
                    len(row) >= 2
                    and row[0] == "Financial Instrument Information"
                    and row[1] == "Header"
                    and row[3] == "Symbol"
                    and row[6] == "Security ID"
                ):
                    logger.debug("Found Financial Instrument Information header")
                    break
            # The loop did not encounter a break statement
            else:
                # The 'else' clause on a for-loop runs only if the loop didn't break
                raise FileProcessingError("Missing 'Financial Instrument Information' header in CSV")


            # NOTE:
            # The csv_reader is an iterator tied to the file handle.
            # When 'break' is used above, the reader's position stays right after the matched line.
            # The next loop below will continue reading from this point — NOT from the start of the file.
            processed_count = 0
            for row in csv_reader:
                if len(row) < 7:
                    continue

                if row[0] != "Financial Instrument Information":
                    break

                if row[1] == "Data" and row[2] == "Stocks":
                    symbol = row[3] if len(row) > 3 else ""
                    isin = row[6] if len(row) > 6 else ""

                    if symbol and isin:
                        try:
                            country = isin_to_country(isin)
                            security_info[symbol] = {"isin": isin, "country": country}
                            processed_count += 1
                            logger.debug(f"Extracted security info for {symbol}: {isin} ({country})")
                        except Exception as e:
                            logger.warning(f"Failed to extract country for {symbol} with ISIN {isin}: {e}")
                            security_info[symbol] = {"isin": isin, "country": "Unknown"}

        logger.info(f"Extracted security data for {len(security_info)} symbols ({processed_count} with country data)")
        return security_info

    except csv.Error as e:
        raise FileProcessingError(f"CSV parsing error while extracting security info: {e}") from e
    except UnicodeDecodeError as e:
        raise FileProcessingError(f"File encoding error while extracting security info: {e}") from e
    except OSError as e:
        raise FileProcessingError(f"File access error while extracting security info: {e}") from e
    except FileProcessingError:
        # Allow explicit FileProcessingError (e.g., missing header) to bubble up unchanged
        raise
    except Exception as e:
        raise SecurityInfoExtractionError(f"Unexpected error while extracting security info: {e}") from e


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
        security_info = extract_security_info(validated_path)
        logger.info(f"Found security data for {len(security_info)} symbols")
    except Exception as e:
        raise FileProcessingError(f"Failed to extract security info: {e}") from e

    trade_cycles_per_company: TradeCyclePerCompany = {}

    try:
        with open(validated_path, "r", encoding="utf-8") as read_obj:
            csv_reader = csv.reader(read_obj)

            for row in csv_reader:
                if len(row) >= 2 and row[0] == "Trades" and row[1] == "Header":
                    headers = row
                    logger.debug("Found Trades section header")
                    break
            else:
                raise FileProcessingError("No Trades section found in the IB export file")

            try:
                col_mapping = {
                    "symbol": headers.index("Symbol"),
                    "currency": headers.index("Currency"),
                    "datetime": headers.index("Date/Time"),
                    "quantity": headers.index("Quantity"),
                    "price": headers.index("T. Price"),
                    "fee": headers.index("Comm/Fee"),
                }
                logger.debug(f"Column mapping: {col_mapping}")
            except ValueError as e:
                raise FileProcessingError(f"Missing required column in Trades section: {e}") from e

            processed_trades = 0
            skipped_trades = 0

            for row in csv_reader:
                if len(row) < len(headers):
                    skipped_trades += 1
                    continue

                if row[0] != "Trades" or row[1] != "Data":
                    continue

                if len(row) > 2 and (row[2] != "Order" or row[3] != "Stocks"):
                    skipped_trades += 1
                    continue

                datetime_val = (
                    row[col_mapping["datetime"]]
                    if len(row) > col_mapping["datetime"]
                    else ""
                )
                if not datetime_val or datetime_val.strip() == "":
                    skipped_trades += 1
                    continue

                symbol = (
                    row[col_mapping["symbol"]] if len(row) > col_mapping["symbol"] else ""
                )
                currency_str = (
                    row[col_mapping["currency"]]
                    if len(row) > col_mapping["currency"]
                    else ""
                )
                quantity = (
                    row[col_mapping["quantity"]]
                    if len(row) > col_mapping["quantity"]
                    else ""
                )
                price = row[col_mapping["price"]] if len(row) > col_mapping["price"] else ""
                fee = row[col_mapping["fee"]] if len(row) > col_mapping["fee"] else ""

                if not symbol:
                    skipped_trades += 1
                    continue

                try:
                    symbol_info = security_info.get(symbol, {})
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

                    processed_trades += 1

                    if processed_trades <= 5 or processed_trades % 100 == 0:
                        logger.debug(f"Processed trade {processed_trades}: {symbol} {currency_str} {quantity} @ {price}")

                except Exception as e:
                    logger.warning(f"Failed to process trade for {symbol}: {e}")
                    skipped_trades += 1
                    continue

            logger.info(f"Processed {processed_trades} trades for {len(trade_cycles_per_company)} currency-company pairs")
            if skipped_trades > 0:
                logger.warning(f"Skipped {skipped_trades} invalid trades")

    except csv.Error as e:
        raise FileProcessingError(f"CSV parsing error in trade processing: {e}") from e
    except UnicodeDecodeError as e:
        raise FileProcessingError(f"File encoding error in trade processing: {e}") from e
    except OSError as e:
        raise FileProcessingError(f"File access error in trade processing: {e}") from e
    except Exception as e:
        raise FileProcessingError(f"Unexpected error in trade processing: {e}") from e

    return trade_cycles_per_company


