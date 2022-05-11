import csv
from os import PathLike
from pathlib import Path

import openpyxl
from typing import Union

from trade_classes import TradeActionsPerCompany, TradeActions, TradeAction, TradeActionList


def parse_data(path: Union[str, Path[str]]) -> TradeActionsPerCompany:
    print("This line will be printed.")
    print(path)

    trade_actions_per_company: TradeActionsPerCompany = {}
    trade_actions: TradeActions = {}
    with open(path, 'r') as read_obj:
        csv_dict_reader = csv.DictReader(read_obj)
        for row in csv_dict_reader:
            if row["Date/Time"] != "":
                company = row["Symbol"]
                if company in trade_actions_per_company.keys():
                    trade_actions = trade_actions_per_company[company]

                t = TradeAction(company, row["Date/Time"], row["Currency"], row["Quantity"], row["T. Price"],
                                row["Comm/Fee"])
                if t.trade_type in trade_actions:
                    trade_action_list: TradeActionList = trade_actions[t.trade_type]
                else:
                    trade_action_list: TradeActionList = []
                trade_action_list.append((t.quantity, t))
                trade_actions[t.trade_type] = trade_action_list
                trade_actions_per_company[company] = trade_actions

    return trade_actions_per_company


# Doesn't seem valuable - too much information is lost while converting to xlsx.
# Let's just create test object
def parse_results(path: Union[str, PathLike[str]]):
    xlsx_file = Path('resources', 'capital_gains.xlsx')
    print("This line will be printed.")
    print(path)

    wb_obj = openpyxl.load_workbook(xlsx_file)
    # Read the active sheet:
    sheet = wb_obj.active
    col_names = []
    for column in sheet.iter_cols(1, sheet.max_column):
        col_names.append(column[0].value)

    print(col_names)
