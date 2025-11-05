import csv
from pathlib import Path
from typing import Dict, Optional, Union

from ..domain.collections import QuantitatedTradeActions, TradeCyclePerCompany
from ..domain.entities import (
    CurrencyCompany,
    QuantitatedTradeAction,
    TradeAction,
    TradeCycle,
)
from ..domain.value_objects import get_company, get_currency
from ..infrastructure.isin_country import isin_to_country


def extract_isin_mapping(path: Union[str, Path]) -> Dict[str, Dict[str, str]]:
    """
    Extract ISIN and country information from raw Interactive Brokers export.

    Parses the "Financial Instrument Information" sections to build a mapping
    of ticker symbols to their ISIN codes and countries of issuance.

    Args:
        path: Path to the raw IB export CSV file

    Returns:
        Dictionary mapping symbol -> {'isin': str, 'country': str}
    """
    isin_mapping: Dict[str, Dict[str, str]] = {}

    with open(path, "r", encoding="utf-8") as read_obj:
        csv_reader = csv.reader(read_obj)

        # Skip header rows until we find Financial Instrument Information section
        for row in csv_reader:
            if (
                len(row) >= 2
                and row[0] == "Financial Instrument Information"
                and row[1] == "Header"
            ):
                # Found the header, now look for the data rows
                break

        # Process the data rows
        for row in csv_reader:
            if len(row) < 7:
                continue

            # Stop if we hit the next section
            if row[0] != "Financial Instrument Information":
                break

            if row[1] == "Data" and row[2] == "Stocks":
                # Extract data from Financial Instrument Information rows
                # Format: Financial Instrument Information,Data,Stocks,Symbol,Description,Conid,Security ID,...
                symbol = row[3] if len(row) > 3 else ""
                isin = row[6] if len(row) > 6 else ""

                if symbol and isin:
                    country = isin_to_country(isin)
                    isin_mapping[symbol] = {"isin": isin, "country": country}

    return isin_mapping


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
    print(f"Processing raw IB export: {path}")

    # First, extract ISIN mapping from the file
    isin_mapping = extract_isin_mapping(path)
    print(f"Found ISIN data for {len(isin_mapping)} symbols")

    trade_cycles_per_company: TradeCyclePerCompany = {}

    with open(path, "r", encoding="utf-8") as read_obj:
        csv_reader = csv.reader(read_obj)

        # Find the Trades section
        for row in csv_reader:
            if len(row) >= 2 and row[0] == "Trades" and row[1] == "Header":
                # Found trades header, extract column indices
                headers = row
                break
        else:
            raise ValueError("No Trades section found in the IB export file")

        # Create column mapping
        try:
            col_mapping = {
                "symbol": headers.index("Symbol"),
                "currency": headers.index("Currency"),
                "datetime": headers.index("Date/Time"),
                "quantity": headers.index("Quantity"),
                "price": headers.index("T. Price"),
                "fee": headers.index("Comm/Fee"),
            }
        except ValueError as e:
            raise ValueError(f"Missing required column in Trades section: {e}")

        # Process trade rows
        for row in csv_reader:
            if len(row) < len(headers):
                continue

            # Stop if we hit another section
            if row[0] != "Trades" or row[1] != "Data":
                continue

            # Skip non-stock trades (we want data of type "Order" and Asset Category = Stocks)
            if len(row) > 2 and (row[2] != "Order" or row[3] != "Stocks"):
                continue

            # Skip empty datetime rows
            datetime_val = (
                row[col_mapping["datetime"]]
                if len(row) > col_mapping["datetime"]
                else ""
            )
            if not datetime_val or datetime_val.strip() == "":
                continue

            # Extract trade data
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
                continue

            # Get ISIN and country info if available
            symbol_info = isin_mapping.get(symbol, {})
            isin = symbol_info.get("isin", "")
            country = symbol_info.get("country", "Unknown")

            # Create enriched Company object
            company = get_company(symbol, isin, country)
            currency = get_currency(currency_str)

            # Create or get trade cycle for this currency-company pair
            currency_company: CurrencyCompany = CurrencyCompany(
                currency=currency, company=company
            )
            if currency_company in trade_cycles_per_company:
                trade_cycle: TradeCycle = trade_cycles_per_company[currency_company]
            else:
                trade_cycle: TradeCycle = TradeCycle()
                trade_cycles_per_company[currency_company] = trade_cycle

            # Create trade action
            trade_action = TradeAction(
                company, datetime_val, currency, quantity, price, fee
            )
            quantitated_trade_actions: QuantitatedTradeActions = trade_cycle.get(
                trade_action.trade_type
            )
            quantitated_trade_actions.append(
                QuantitatedTradeAction(trade_action.quantity, trade_action)
            )

    print(
        f"Processed trades for {len(trade_cycles_per_company)} currency-company pairs"
    )
    return trade_cycles_per_company


