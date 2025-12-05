import csv
import re
from decimal import Decimal
from pathlib import Path

from ...domain.collections import (
    DividendIncomePerCompany,
    IBExportData,
    QuantitatedTradeActions,
    TradeCyclePerCompany,
)
from ...domain.entities import (
    CurrencyCompany,
    DividendIncomePerSecurity,
    QuantitatedTradeAction,
    TradeAction,
    TradeCycle,
)
from ...domain.exceptions import FileProcessingError, SecurityInfoExtractionError
from ...domain.value_objects import (
    parse_company,
    parse_currency,
)
from ...infrastructure.logging_config import create_module_logger
from .models import IBCsvData
from .state_machine import IBCsvStateMachine


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
            quantitated_trade_actions: QuantitatedTradeActions = trade_cycle.get(trade_action.trade_type)
            quantitated_trade_actions.append(QuantitatedTradeAction(trade_action.quantity, trade_action))

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
    aggregation: dict[str, dict[str, Decimal]] = {}  # symbol -> {gross_amount, total_taxes, currency}

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
            tax_amount = Decimal(tax_amount_str.replace(",", "")) if tax_amount_str else Decimal("0")
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
        logger.info(f"Extracting CSV data from: {validated_path.name}")
        csv_data = _extract_csv_data(validated_path)
        logger.info(f"Extracted CSV data from: {validated_path.name}")
        trade_cycles = _process_trades(csv_data)
        logger.info(f"Processed trades from: {validated_path.name}")
        dividend_income = _process_dividends(csv_data)
        logger.info(f"Processed dividends from: {validated_path.name}")

        return IBExportData(trade_cycles=trade_cycles, dividend_income=dividend_income)
    except Exception as e:
        raise FileProcessingError(f"Failed to parse complete IB export: {e}") from e
