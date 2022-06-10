import os
from os import PathLike
import openpyxl
from typing import Union, List, Tuple

from openpyxl import Workbook

from config import Config, read_config, ConversionRate
from domain import CapitalGainLinesPerCompany, CurrencyToCoordinates, CurrencyToCoordinate

first_header = ["Beneficiary", "Country of Source", "SALE", "", "", "PURCHASE", "", "",
                "WITHOLDING TAX", "", "Expenses incurred with obtaining the capital gains", "",
                "Symbol", "Currency", "Sale amount", "Buy amount", "Expenses amount"]
second_header = ["", "", "Month ", "Year", "Amount", "Month ", "Year", "Amount", "Country", "Amount",
                 "", "", "", "", "", "", ""]
currency_header = ["Base/target", "Rate"]

last_column: int = max(len(first_header), len(second_header))


def safe_remove_file(path: Union[str, PathLike[str]]):
    if os.path.exists(path):
        os.remove(path)


# https://openpyxl.readthedocs.io/en/latest/tutorial.html
def create_currency_table(worksheet: Workbook, column_no: int, row_no: int, rates: List[ConversionRate]) \
        -> CurrencyToCoordinates:
    worksheet.cell(row_no, column_no, "Currency exchange rate")
    row_no += 1
    for i in range(len(currency_header)):
        worksheet.cell(row_no, column_no, currency_header[i])

    result: CurrencyToCoordinates = []
    for j in range(len(rates)):
        worksheet.cell(row_no + j, column_no, rates[j].base + "/" + rates[j].calculated)
        cell = worksheet.cell(row_no + j, column_no + 1, str(rates[j].rate))
        result.append(CurrencyToCoordinate(currency=rates[j].calculated, coordinate=cell.coordinate))

    return result


def persist_results(path: Union[str, PathLike[str]], capital_gain_lines_per_company: CapitalGainLinesPerCompany):
    number_format = '0.000000'
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Reporting"

    for i in range(len(first_header)):
        worksheet.cell(1, i + 1, first_header[i])
        worksheet.cell(2, i + 1, second_header[i])

    start_column = 3
    line_number = 3
    for currency_company, capital_gain_lines in capital_gain_lines_per_company.items():
        currency = currency_company[0]
        symbol = currency_company[1]
        for line in capital_gain_lines:
            assert currency == line.get_currency()
            idx = start_column
            c = worksheet.cell(line_number, start_column, line.get_sell_date().get_month_name())
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_sell_date().year)
            idx += 2
            c = worksheet.cell(line_number, idx, line.get_buy_date().get_month_name())
            idx += 1
            c = worksheet.cell(line_number, idx, line.get_buy_date().year)
            idx += 6
            c = worksheet.cell(line_number, start_column + 10, symbol)
            idx += 1
            c = worksheet.cell(line_number, start_column + 11, currency)
            idx += 1
            c = worksheet.cell(line_number, start_column + 12, line.get_sell_amount())
            c.number_format = number_format
            idx += 1
            c = worksheet.cell(line_number, start_column + 13, line.get_buy_amount())
            c.number_format = number_format
            idx += 1
            c = worksheet.cell(line_number, start_column + 14, line.get_expense_amount())
            c.number_format = number_format
            line_number += 1

    for column_cells in worksheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

    config: Config = read_config()
    exchange_rates: CurrencyToCoordinates = create_currency_table(worksheet, last_column + 2, 1, config.rates)

    safe_remove_file(path)
    workbook.save(path)
    workbook.close()
