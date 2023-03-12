import csv
from pathlib import Path

from typing import Union

from domain import TradeCyclePerCompany, TradeCycle, TradeAction, QuantitatedTradeActions, CurrencyCompany, get_currency, \
    QuantitatedTradeAction, get_company


def parse_data(path: Union[str, Path[str]]) -> TradeCyclePerCompany:
    print("This line will be printed.")
    print(path)

    trade_actions_per_company: TradeCyclePerCompany = {}
    with open(path, 'r') as read_obj:
        csv_dict_reader = csv.DictReader(read_obj)
        for row in csv_dict_reader:
            if row["Date/Time"] != "":
                company = get_company(row["Symbol"])
                currency = get_currency(row["Currency"])
                currency_company: CurrencyCompany = CurrencyCompany(currency=currency, company=company)
                if currency_company in trade_actions_per_company.keys():
                    trade_cycle: TradeCycle = trade_actions_per_company[currency_company]
                else:
                    trade_cycle: TradeCycle = TradeCycle()
                    trade_actions_per_company[currency_company] = trade_cycle

                t = TradeAction(company, row["Date/Time"], currency, row["Quantity"], row["T. Price"],
                                row["Comm/Fee"])
                quantitated_trade_actions: QuantitatedTradeActions = trade_cycle.get(t.trade_type)
                quantitated_trade_actions.append(QuantitatedTradeAction(t.quantity, t))
    return trade_actions_per_company
