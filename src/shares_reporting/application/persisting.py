import csv
import os
from typing import Dict, List, Union

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from ..domain.collections import CapitalGainLinesPerCompany, TradeCyclePerCompany
from ..domain.entities import CurrencyCompany, TradeCycle
from ..domain.value_objects import TradeType
from ..infrastructure.config import Config, ConversionRate, read_config
from ..infrastructure.logging_config import get_logger
from ..domain.exceptions import ReportGenerationError
from ..domain.constants import EXCEL_START_COLUMN, EXCEL_START_ROW, EXCEL_HEADER_ROW_1, EXCEL_HEADER_ROW_2, EXCEL_WITHOLDING_TAX_COLUMN, EXCEL_COUNTRY_COLUMN, EXCEL_COLUMN_OFFSET, EXCEL_NUMBER_FORMAT


def persist_leftover(
    leftover: Union[str, os.PathLike], leftover_trades: TradeCyclePerCompany
) -> None:
    """
    Generate a CSV report for leftover (unmatched) trades.

    Args:
        leftover: Output file path for the leftover trades CSV
        leftover_trades: Dictionary of trades that couldn't be matched
    """
    logger = get_logger(__name__)
    logger.info(f"Generating leftover shares report: {Path(leftover).name}")

    safe_remove_file(leftover)
    row = {
        "Trades": "Trades",
        "Header": "Data",
        "DataDiscriminator": "Order",
        "Asset Category": "Stocks",
    }
    currency_company: CurrencyCompany
    trade_cycle: TradeCycle
    processed_companies = 0

    with open(leftover, "w", newline="") as right_obj:
        writer = csv.DictWriter(
            right_obj,
            fieldnames=[
                "Trades",
                "Header",
                "DataDiscriminator",
                "Asset Category",
                "Currency",
                "Symbol",
                "Date/Time",
                "Quantity",
                "T. Price",
                "C. Price",
                "Proceeds",
                "Comm/Fee",
            ],
        )
        writer.writeheader()
        for currency_company, trade_cycle in leftover_trades.items():
            processed_companies += 1
            row["Currency"] = currency_company.currency.currency
            row["Symbol"] = currency_company.company.ticker

            logger.debug(f"Processing leftover trades for {row['Symbol']} ({row['Currency']})")

            # we are not expecting any sold shares in the leftover file
            if trade_cycle.has_bought():
                bought_trades = trade_cycle.get(TradeType.BUY)
                logger.debug(f"Writing {len(bought_trades)} leftover buy trades for {row['Symbol']}")

                for bought_trade in bought_trades:
                    row["Quantity"] = bought_trade.quantity
                    action = bought_trade.action
                    row["Date/Time"] = (
                        str(action.date_time.date())
                        + ", "
                        + str(action.date_time.time())
                    )
                    row["T. Price"] = action.price
                    row["Proceeds"] = action.price * bought_trade.quantity
                    row["Comm/Fee"] = action.fee
                    writer.writerow(row)

    logger.info(f"Generated leftover report for {processed_companies} companies")


def persist_results(
    extract: Union[str, os.PathLike],
    capital_gain_lines_per_company: CapitalGainLinesPerCompany,
) -> None:
    """
    Generate an Excel report with capital gains calculations.

    Args:
        extract: Output file path for the Excel report
        capital_gain_lines_per_company: Calculated capital gains grouped by company
    """
    logger = get_logger(__name__)
    logger.info(f"Generating capital gains report: {Path(extract).name}")

    total_gain_lines = sum(len(lines) for lines in capital_gain_lines_per_company.values())
    logger.debug(f"Processing {total_gain_lines} capital gain lines across {len(capital_gain_lines_per_company)} companies")

    first_header = [
        "Beneficiary",
        "Country of Source",
        "SALE",
        "",
        "",
        "",
        "PURCHASE",
        "",
        "",
        "",
        "WITHOLDING TAX",
        "",
        "Expenses incurred with obtaining the capital gains",
        "",
        "Symbol",
        "Currency",
        "Sale amount",
        "Buy amount",
        "Expenses amount",
    ]
    second_header = [
        "",
        "",
        "Day ",
        "Month ",
        "Year",
        "Amount",
        "Day ",
        "Month ",
        "Year",
        "Amount",
        "Country",
        "Amount",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]

    last_column: int = max(len(first_header), len(second_header))
    number_format = "0.000000"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Reporting"

    try:
        config: Config = read_config()
        exchange_rates: Dict[str, str] = create_currency_table(
            worksheet, last_column + 2, 1, config
        )
        logger.debug(f"Created currency exchange table with {len(config.rates) + 1} rates")
    except Exception as e:
        raise ReportGenerationError(f"Failed to read configuration for currency exchange: {e}") from e

    for i in range(len(first_header)):
        worksheet.cell(EXCEL_HEADER_ROW_1, i + 1, first_header[i])
        worksheet.cell(EXCEL_HEADER_ROW_2, i + 1, second_header[i])

    start_column = EXCEL_START_COLUMN
    line_number = EXCEL_START_ROW
    processed_lines = 0

    for currency_company, capital_gain_lines in capital_gain_lines_per_company.items():
        currency = currency_company.currency
        company = currency_company.company
        logger.debug(f"Processing capital gain lines for {company.ticker} ({currency.currency})")

        for line in capital_gain_lines:
            assert currency == line.get_currency()
            processed_lines += 1
            idx = start_column

            # SALE information
            c = worksheet.cell(line_number, start_column, line.get_sell_date().day)
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_sell_date().get_month_name())
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_sell_date().year)
            idx += 1
            c = worksheet.cell(
                line_number,
                idx,
                "="
                + exchange_rates[currency.currency]
                + "*("
                + line.get_sell_amount()
                + ")",
            )

            # PURCHASE information
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_buy_date().day)
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_buy_date().get_month_name())
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_buy_date().year)
            idx += 1
            c = worksheet.cell(
                line_number,
                idx,
                "="
                + exchange_rates[currency.currency]
                + "*("
                + line.get_buy_amount()
                + ")",
            )

            # WITHOLDING TAX information (skip Country and Amount columns for now)
            idx += EXCEL_COLUMN_OFFSET

            # EXPENSES information
            c = worksheet.cell(
                line_number,
                idx,
                "="
                + exchange_rates[currency.currency]
                + "*("
                + line.get_expense_amount()
                + ")",
            )
            idx += 2

            # Symbol and Currency
            c = worksheet.cell(line_number, idx, company.ticker)
            idx += 1
            c = worksheet.cell(line_number, idx, currency.currency)
            idx += 1

            # Amounts section
            c = worksheet.cell(line_number, idx, "=" + line.get_sell_amount())
            c.number_format = EXCEL_NUMBER_FORMAT
            idx += 1
            c = worksheet.cell(line_number, idx, "=" + line.get_buy_amount())
            c.number_format = EXCEL_NUMBER_FORMAT
            idx += 1
            c = worksheet.cell(line_number, idx, "=" + line.get_expense_amount())
            c.number_format = EXCEL_NUMBER_FORMAT

            line_number += 1

    logger.debug(f"Processed {processed_lines} capital gain lines")

    # Populate Country of Source column for all rows
    # This is done after the main loop to ensure we have all data
    line_number = EXCEL_START_ROW
    for currency_company, capital_gain_lines in capital_gain_lines_per_company.items():
        company = currency_company.company
        for line in capital_gain_lines:
            # Column 2 is "Country of Source" (according to first_header array)
            country_cell = worksheet.cell(line_number, 2, company.country_of_issuance)

            # Populate WITHOLDING TAX Country (Column 11 according to first_header array)
            tax_country_cell = worksheet.cell(
                line_number, 11, company.country_of_issuance
            )

            line_number += 1

    # auto width for the populated cells
    logger.debug("Auto-adjusting column widths")
    for column_cells in worksheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

    safe_remove_file(extract)

    try:
        workbook.save(extract)
        workbook.close()
        logger.info(f"Successfully generated capital gains report with {processed_lines} lines")
    except Exception as e:
        raise ReportGenerationError(f"Failed to save Excel report: {e}") from e


def safe_remove_file(path: Union[str, os.PathLike]) -> None:
    """
    Safely remove a file if it exists, logging any errors.

    Args:
        path: File path to remove
    """
    logger = get_logger(__name__)
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.debug(f"Removed existing file: {Path(path).name}")
    except OSError as e:
        logger.warning(f"Failed to remove file {path}: {e}")
        # Non-critical error, continue processing


# https://openpyxl.readthedocs.io/en/latest/tutorial.html
def create_currency_table(
    worksheet: Worksheet, column_no: int, row_no: int, config: Config
) -> Dict[str, str]:
    logger = get_logger(__name__)
    currency_header = ["Base/target", "Rate"]
    rates: List[ConversionRate] = config.rates

    logger.debug(f"Creating currency table starting at column {column_no}, row {row_no}")

    worksheet.cell(row_no, column_no, "Currency exchange rate")
    row_no += 1
    for i in range(len(currency_header)):
        worksheet.cell(row_no, column_no, currency_header[i])

    coordinates: Dict[str, str] = {}
    for j in range(len(rates)):
        worksheet.cell(row_no + j, column_no, rates[j].base + "/" + rates[j].calculated)
        cell = worksheet.cell(row_no + j, column_no + 1, str(rates[j].rate))
        coordinates[rates[j].calculated] = cell.coordinate
        logger.debug(f"Added currency rate {rates[j].base}/{rates[j].calculated} = {rates[j].rate}")

    # Add base currency rate (1:1)
    worksheet.cell(row_no + len(rates), column_no, config.base + "/" + config.base)
    cell = worksheet.cell(row_no + len(rates), column_no + 1, "1")
    coordinates[config.base] = cell.coordinate
    logger.debug(f"Added base currency {config.base}/{config.base} = 1")

    logger.debug(f"Created currency table with {len(coordinates)} exchange rates")
    return coordinates
