import csv
from os import PathLike
from pathlib import Path

import openpyxl
from typing import Union

from supplementary import TradeActionsPerCompany, TradeActions, TradeAction, TradeActionList


def parse_data(path: Union[str, Path[str]]) -> TradeActionsPerCompany:
    print("This line will be printed.")
    print(path)

    trade_actions_per_company: TradeActionsPerCompany = {}
    with open(path, 'r') as read_obj:
        csv_dict_reader = csv.DictReader(read_obj)
        for row in csv_dict_reader:
            if row["Date/Time"] != "":
                company = row["Symbol"]
                currency = row["Currency"]
                currency_company = (currency, company)
                if currency_company in trade_actions_per_company.keys():
                    trade_actions: TradeActions = trade_actions_per_company[currency_company]
                else:
                    trade_actions: TradeActions = {}

                t = TradeAction(company, row["Date/Time"], currency, row["Quantity"], row["T. Price"],
                                row["Comm/Fee"])
                if t.trade_type in trade_actions.keys():
                    trade_action_list: TradeActionList = trade_actions[t.trade_type]
                else:
                    trade_action_list: TradeActionList = []
                trade_action_list.append((t.quantity, t))
                trade_actions[t.trade_type] = trade_action_list
                trade_actions_per_company[currency_company] = trade_actions

    return trade_actions_per_company
