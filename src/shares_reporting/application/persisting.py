"""Persistence layer containing logic for generating reports and saving data."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from ..domain.collections import (
    CapitalGainLinesPerCompany,
    DividendIncomePerCompany,
    TradeCyclePerCompany,
)
from ..domain.constants import (
    EXCEL_COLUMN_OFFSET,
    EXCEL_HEADER_ROW_1,
    EXCEL_HEADER_ROW_2,
    EXCEL_NUMBER_FORMAT,
    EXCEL_START_COLUMN,
    EXCEL_START_ROW,
    PLACEHOLDER_YEAR,
    ZERO_QUANTITY,
)
from ..domain.exceptions import ReportGenerationError
from ..domain.value_objects import TradeType
from ..infrastructure.config import Config, ConversionRate, load_configuration_from_file
from ..infrastructure.logging_config import create_module_logger


def export_rollover_file(leftover: str | os.PathLike, leftover_trades: TradeCyclePerCompany) -> None:
    """Export unmatched securities rollover file for next year's FIFO calculations.

    This function creates a CSV file containing all trades that couldn't be matched
    during the FIFO capital gains calculation process. These unmatched securities
    are rolled over to the next tax year to maintain FIFO continuity.

    Args:
        leftover: Output file path for the unmatched securities rollover file
        leftover_trades: Dictionary of trades to be rolled over to next year's calculations
    """
    logger = create_module_logger(__name__)
    logger.info("Generating unmatched securities rollover file: %s", Path(leftover).name)

    safe_remove_file(leftover)
    processed_companies = ZERO_QUANTITY

    with Path(leftover).open("w", newline="") as right_obj:
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
            row = {
                "Trades": "Trades",
                "Header": "Data",
                "DataDiscriminator": "Order",
                "Asset Category": "Stocks",
                "Currency": currency_company.currency.currency,
                "Symbol": currency_company.company.ticker,
            }

            logger.debug("Processing leftover trades for %s (%s)", row["Symbol"], row["Currency"])

            # we are not expecting any sold shares in the leftover file
            if trade_cycle.has_bought():
                bought_trades = trade_cycle.get(TradeType.BUY)
                logger.debug("Writing %s leftover buy trades for %s", len(bought_trades), row["Symbol"])

                for bought_trade in bought_trades:
                    row["Quantity"] = str(bought_trade.quantity)
                    action = bought_trade.action
                    row["Date/Time"] = str(action.date_time.date()) + ", " + str(action.date_time.time())
                    row["T. Price"] = str(action.price)
                    row["Proceeds"] = str(action.price * bought_trade.quantity)
                    row["Comm/Fee"] = str(action.fee)
                    writer.writerow(row)

    logger.info("Generated unmatched securities rollover file for %s companies", processed_companies)


def generate_tax_report(  # noqa: PLR0912, PLR0915
    extract: str | os.PathLike,
    capital_gain_lines_per_company: CapitalGainLinesPerCompany,
    dividend_income_per_company: DividendIncomePerCompany | None = None,
) -> None:
    """Generate comprehensive Excel tax report with capital gains and dividend income.

    This function creates a professional Excel report containing all tax-relevant
    information for capital gains and dividend income reporting, including currency
    exchange rate tables and proper formatting for submission to tax authorities.

    Args:
        extract: Output file path for the Excel tax report
        capital_gain_lines_per_company: Calculated capital gains grouped by company
        dividend_income_per_company: Dividend income data grouped by company (optional)
    """
    logger = create_module_logger(__name__)
    logger.info("Generating capital gains report: %s", Path(extract).name)

    total_gain_lines = sum(len(lines) for lines in capital_gain_lines_per_company.values())
    logger.debug(
        "Processing %s capital gain lines across %s companies",
        total_gain_lines,
        len(capital_gain_lines_per_company),
    )

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
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Reporting"

    try:
        config: Config = load_configuration_from_file()
        exchange_rates: dict[str, str] = create_currency_table(worksheet, last_column + 2, 1, config)
        logger.debug("Created currency exchange table with %s rates", len(config.rates) + 1)
    except Exception as e:
        raise ReportGenerationError(f"Failed to read configuration for currency exchange: {e}") from e

    for i in range(len(first_header)):
        worksheet.cell(EXCEL_HEADER_ROW_1, i + 1, first_header[i])
        worksheet.cell(EXCEL_HEADER_ROW_2, i + 1, second_header[i])

    start_column = EXCEL_START_COLUMN
    line_number = EXCEL_START_ROW
    processed_lines = ZERO_QUANTITY

    for currency_company, capital_gain_lines in capital_gain_lines_per_company.items():
        currency = currency_company.currency
        company = currency_company.company
        logger.debug("Processing capital gain lines for %s (%s)", company.ticker, currency.currency)

        for line in capital_gain_lines:
            if currency != line.get_currency():
                raise ReportGenerationError(f"Currency mismatch in line: {currency} != {line.get_currency()}")
            processed_lines += 1
            idx = start_column

            # SALE information
            worksheet.cell(line_number, start_column, line.get_sell_date().day)
            idx += 1
            worksheet.cell(line_number, idx, line.get_sell_date().get_month_name())
            idx += 1
            worksheet.cell(line_number, idx, line.get_sell_date().year)
            idx += 1
            worksheet.cell(
                line_number,
                idx,
                "=" + exchange_rates[currency.currency] + "*(" + line.get_sell_amount() + ")",
            )

            # PURCHASE information
            idx += 1
            worksheet.cell(line_number, idx, line.get_buy_date().day)
            idx += 1
            worksheet.cell(line_number, idx, line.get_buy_date().get_month_name())
            idx += 1
            worksheet.cell(line_number, idx, line.get_buy_date().year)
            idx += 1
            worksheet.cell(
                line_number,
                idx,
                "=" + exchange_rates[currency.currency] + "*(" + line.get_buy_amount() + ")",
            )

            # WITHOLDING TAX information (skip Country and Amount columns for now)
            idx += EXCEL_COLUMN_OFFSET

            # EXPENSES information
            expense_cell = worksheet.cell(
                line_number,
                idx,
                "=" + exchange_rates[currency.currency] + "*(" + line.get_expense_amount() + ")",
            )
            expense_cell.number_format = EXCEL_NUMBER_FORMAT
            idx += 2

            # Symbol and Currency
            worksheet.cell(line_number, idx, company.ticker)
            idx += 1
            worksheet.cell(line_number, idx, currency.currency)
            idx += 1

            # Amounts section
            sell_amount_cell = worksheet.cell(line_number, idx, "=" + line.get_sell_amount())
            sell_amount_cell.number_format = EXCEL_NUMBER_FORMAT
            idx += 1
            buy_amount_cell = worksheet.cell(line_number, idx, "=" + line.get_buy_amount())
            buy_amount_cell.number_format = EXCEL_NUMBER_FORMAT
            idx += 1
            expense_amount_cell = worksheet.cell(line_number, idx, "=" + line.get_expense_amount())
            expense_amount_cell.number_format = EXCEL_NUMBER_FORMAT

            # Highlight placeholder buy transactions in red
            if line.get_buy_date().year == PLACEHOLDER_YEAR:
                red_fill = PatternFill(start_color="FFFF0000", end_color="FFFF0000", fill_type="solid")
                # Apply red fill to entire row
                for col_idx in range(start_column, idx + 1):
                    cell = worksheet.cell(line_number, col_idx)
                    cell.fill = red_fill

            line_number += 1

    logger.debug("Processed %s capital gain lines", processed_lines)

    # Populate Country of Source column for all rows
    # This is done after the main loop to ensure we have all data
    line_number = EXCEL_START_ROW
    for currency_company, capital_gain_lines in capital_gain_lines_per_company.items():
        company = currency_company.company
        for _ in capital_gain_lines:
            # Column 2 is "Country of Source" (according to first_header array)
            worksheet.cell(line_number, 2, company.country_of_issuance)

            # Populate WITHOLDING TAX Country (Column 11 according to first_header array)
            worksheet.cell(line_number, 11, company.country_of_issuance)

            line_number += 1

    # Add CAPITAL INVESTMENT INCOME section if dividend data is provided
    if dividend_income_per_company:
        logger.info("Adding CAPITAL INVESTMENT INCOME section with %s securities", len(dividend_income_per_company))

        # Add empty row for spacing
        line_number += 1

        # Section title "5. CAPITAL INVESTMENT INCOME:"
        section_title_cell = worksheet.cell(line_number, 1, "5. CAPITAL INVESTMENT INCOME:")
        section_title_cell.font = openpyxl.styles.Font(bold=True)
        line_number += 1

        # Empty row
        line_number += 1

        # Dividend income headers
        dividend_headers = [
            "Beneficiary\n(choose one)",
            "Type of capital income\n(choose one)",
            "Country of source",
            "ISIN",
            "Gross amount",
            "Withholding tax at source",
            "Withholding tax in Portugal\n(if any)",
            "",  # One empty column separator
            "Symbol",
            "Currency",
            "Original gross amount",
            "Original tax amount",
            "Net amount",
        ]

        for i, header in enumerate(dividend_headers):
            worksheet.cell(line_number, i + 1, header)

        line_number += 1

        # Dividend income data rows
        for symbol, dividend_data in dividend_income_per_company.items():
            worksheet.cell(line_number, 1, "")  # Beneficiary column
            worksheet.cell(line_number, 2, "Dividends")  # Type of capital income
            worksheet.cell(line_number, 3, dividend_data.country)  # Country of source
            worksheet.cell(line_number, 4, dividend_data.isin)  # ISIN

            # Convert amounts using exchange rates and add Excel formulas
            gross_amount_cell = worksheet.cell(
                line_number,
                5,
                "=" + exchange_rates[dividend_data.currency.currency] + "*(" + str(dividend_data.gross_amount) + ")",
            )
            gross_amount_cell.number_format = EXCEL_NUMBER_FORMAT

            tax_amount_cell = worksheet.cell(
                line_number,
                6,
                "=" + exchange_rates[dividend_data.currency.currency] + "*(" + str(dividend_data.total_taxes) + ")",
            )
            tax_amount_cell.number_format = EXCEL_NUMBER_FORMAT

            worksheet.cell(line_number, 7, "")  # Withholding tax in Portugal (empty for now)

            # Symbol and Currency columns (new columns)
            worksheet.cell(line_number, 9, symbol)  # Symbol column
            worksheet.cell(line_number, 10, dividend_data.currency.currency)  # Currency column

            # Original amounts in original currency (new columns)
            original_gross_cell = worksheet.cell(line_number, 11, str(dividend_data.gross_amount))
            original_gross_cell.number_format = EXCEL_NUMBER_FORMAT

            original_tax_cell = worksheet.cell(line_number, 12, str(dividend_data.total_taxes))
            original_tax_cell.number_format = EXCEL_NUMBER_FORMAT

            # Net amount (gross - tax) in original currency (new column)
            net_amount = dividend_data.gross_amount - dividend_data.total_taxes
            net_amount_cell = worksheet.cell(line_number, 13, str(net_amount))
            net_amount_cell.number_format = EXCEL_NUMBER_FORMAT

            logger.debug(
                "Added dividend income row for %s: %s gross, %s tax, %s net (%s)",
                symbol,
                dividend_data.gross_amount,
                dividend_data.total_taxes,
                net_amount,
                dividend_data.currency.currency,
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
        report_type = "capital gains and dividend income" if dividend_income_per_company else "capital gains"
        logger.info("Successfully generated %s report with %s capital gain lines", report_type, processed_lines)
    except Exception as e:
        raise ReportGenerationError(f"Failed to save Excel report: {e}") from e


def safe_remove_file(path: str | os.PathLike) -> None:
    """Safely remove a file if it exists, logging any errors.

    Args:
        path: File path to remove
    """
    logger = create_module_logger(__name__)
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
            logger.debug("Removed existing file: %s", p.name)
    except OSError as e:
        logger.warning("Failed to remove file %s: %s", path, e)
        # Non-critical error, continue processing


# https://openpyxl.readthedocs.io/en/latest/tutorial.html
def create_currency_table(worksheet: Worksheet, column_no: int, row_no: int, config: Config) -> dict[str, str]:
    """Create a currency configuration table in the excel worksheet.

    Args:
        worksheet: The target excel worksheet.
        column_no: The starting column number (1-based).
        row_no: The starting row number (1-based).
        config: The application configuration object.

    Returns:
        A dictionary mapping cell coordinates to their formatted values.
    """
    logger = create_module_logger(__name__)
    currency_header = ["Base/target", "Rate"]
    rates: list[ConversionRate] = config.rates

    logger.debug("Creating currency table starting at column %s, row %s", column_no, row_no)

    worksheet.cell(row_no, column_no, "Currency exchange rate")
    row_no += 1
    for i in range(len(currency_header)):
        worksheet.cell(row_no, column_no, currency_header[i])

    coordinates: dict[str, str] = {}
    for j in range(len(rates)):
        worksheet.cell(row_no + j, column_no, rates[j].base + "/" + rates[j].calculated)
        cell = worksheet.cell(row_no + j, column_no + 1, str(rates[j].rate))
        coordinates[rates[j].calculated] = cell.coordinate
        logger.debug("Added currency rate %s/%s = %s", rates[j].base, rates[j].calculated, rates[j].rate)

    # Add base currency rate (1:1)
    worksheet.cell(row_no + len(rates), column_no, config.base + "/" + config.base)
    cell = worksheet.cell(row_no + len(rates), column_no + 1, "1")
    coordinates[config.base] = cell.coordinate
    logger.debug("Added base currency %s/%s = 1", config.base, config.base)

    logger.debug("Created currency table with %s exchange rates", len(coordinates))
    return coordinates
