"""Core processing logic for extracting data from IB CSV exports."""

from __future__ import annotations

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
from ...domain.constants import DECIMAL_ZERO
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
    """Collect all raw data from IB export CSV file using a state machine approach.

    This function reads the file once and extracts security information,
    raw trade data, and dividend data for deferred processing using a proper
    state machine pattern.

    Args:
        path: Path to the raw IB export CSV file
        require_trades_section: If True, requires Trades section to be present (default True)

    Returns:
        IBCsvData container with all collected information
    """
    try:
        # Initialize state machine
        state_machine = IBCsvStateMachine(require_trades_section)

        # Process CSV file row by row using state machine
        with Path(path).open(encoding="utf-8") as read_obj:
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
    """Process raw trade data using complete security information.

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
                trade_cycle = trade_cycles_per_company[currency_company]
            else:
                trade_cycle = TradeCycle()
                trade_cycles_per_company[currency_company] = trade_cycle

            trade_action = TradeAction(company, datetime_val, currency, quantity, price, fee)
            quantitated_trade_actions: QuantitatedTradeActions = trade_cycle.get(trade_action.trade_type)
            quantitated_trade_actions.append(QuantitatedTradeAction(trade_action.quantity, trade_action))

        except Exception as e:
            raise FileProcessingError("Failed to process trade for symbol %s: %s", symbol, e) from e

    logger.info(
        "Processed %d trades for %d currency-company pairs",
        len(csv_data.raw_trade_data),
        len(trade_cycles_per_company),
    )
    return trade_cycles_per_company


def _process_dividends(csv_data: IBCsvData) -> DividendIncomePerCompany:  # noqa: PLR0912, PLR0915
    """Process raw dividend data using complete security information.

    This function aggregates dividend amounts per security for capital investment
    income reporting, using the complete security context (ISIN, country).

    Args:
        csv_data: IBCsvData container with security_info and raw_dividend_data

    Returns:
        DividendIncomePerCompany mapping symbol to aggregated dividend data
    """
    logger = create_module_logger(__name__)
    dividend_income_per_company: DividendIncomePerCompany = {}

    # Combine data sources: Dividends section and Withholding Tax section
    # We tag them to know if they are explicitly taxes
    # item: (row_dict, is_explicitly_tax)
    all_rows = [(row, False) for row in csv_data.raw_dividend_data] + [
        (row, True) for row in csv_data.raw_withholding_tax_data
    ]

    for div_row, is_explicitly_tax in all_rows:
        description = div_row["description"]

        # Try to extract symbol from description if not present
        # Format in IB CSV: "SYMBOL(ISIN) Description" or "SYMBOL Description"
        # Examples:
        #   "PARA(US92556H2067) Payment in Lieu of Dividend (Ordinary Dividend)"
        #   "BTG (CA11777Q2099) Cash Dividend USD 0.04 (Ordinary Dividend)"
        #   "NVDA(US67066G1040) Cash Dividend USD 0.04 per Share (Ordinary Dividend)"
        symbol = div_row.get("symbol")
        if not symbol:
            # Regex to match SYMBOL at start, optional space + (ISIN), then space
            match = re.match(r"^([A-Z0-9]+)(?:\s*\([A-Z0-9]+\))?\s+", description)
            if match:
                symbol = match.group(1)
            else:
                logger.debug("Could not extract symbol from dividend description: %s", description)
                continue

        currency_str = div_row["currency"]
        amount = div_row["amount"]

        try:
            symbol_info = csv_data.security_info.get(symbol, {})
            isin = symbol_info.get("isin", "")
            country = symbol_info.get("country", "Unknown")

            if not isin:
                # Include missing ISIN entries with error indicators
                logger.error(
                    "Missing security information for symbol %s - including dividend data but "
                    "requires manual review. Please add this security to your IB account or verify "
                    "the symbol.",
                    symbol,
                )
                isin = "MISSING_ISIN_REQUIRES_ATTENTION"
                country = "UNKNOWN_COUNTRY"

            # Simple aggregation key: symbol
            if symbol not in dividend_income_per_company:
                dividend_income_per_company[symbol] = DividendIncomePerSecurity(
                    symbol=symbol,
                    isin=isin,
                    country=country,
                    gross_amount=DECIMAL_ZERO,
                    total_taxes=DECIMAL_ZERO,
                    currency=parse_currency(currency_str),
                )

            agg = dividend_income_per_company[symbol]

            # Identify if this is a tax withholding
            is_tax = is_explicitly_tax or ("Withholding Tax" in description or "Tax" in description)

            if is_tax:
                # Taxes are usually negative in the report, we want positive magnitude for the record
                agg.total_taxes += abs(Decimal(amount))
            else:
                # Gross income
                agg.gross_amount += Decimal(amount)

            # Skip validation for entries with missing ISINs since they're already marked
            if dividend_income_per_company[symbol].isin != "MISSING_ISIN_REQUIRES_ATTENTION":
                agg.validate()

        except SecurityInfoExtractionError as e:
            # This should no longer happen with our new approach, but fail fast if it does
            raise FileProcessingError("Security info error for symbol %s: %s", symbol, e) from e
        except Exception as e:
            raise FileProcessingError("Failed to process dividend/tax for symbol %s: %s", symbol, e) from e

    logger.info(
        "Processed dividend data for %d securities",
        len(dividend_income_per_company),
    )
    return dividend_income_per_company


def parse_ib_export_all(file_path: str | Path) -> IBExportData:
    """Parse IB export file and return all extracted data.

    Args:
        file_path: Path to the IB export CSV file.

    Returns:
        IBExportData object containing collected trade cycles and dividend income.
    """
    csv_data = _extract_csv_data(file_path)

    return IBExportData(
        trade_cycles=_process_trades(csv_data),
        dividend_income=_process_dividends(csv_data),
    )


def parse_ib_export(file_path: str | Path, require_trades_section: bool = True) -> TradeCyclePerCompany:
    """Parse IB export and return trades (backward compatibility).

    Args:
        file_path: Path to the IB export CSV file.
        require_trades_section: Whether to require trades section.

    Returns:
        TradeCyclePerCompany object containing collected trade cycles.
    """
    csv_data = _extract_csv_data(file_path, require_trades_section)
    return _process_trades(csv_data)


def parse_dividend_income(file_path: str | Path) -> DividendIncomePerCompany:
    """Parse IB export and return dividend income (backward compatibility).

    Args:
        file_path: Path to the IB export CSV file.

    Returns:
        DividendIncomePerCompany object containing collected dividend income.
    """
    csv_data = _extract_csv_data(file_path, require_trades_section=False)
    return _process_dividends(csv_data)
