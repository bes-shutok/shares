import os
from decimal import Decimal
from typing import Union

from domain import TradeType, TradeAction, TradeCycle, CapitalGainLines, QuantitatedTradeActions, \
    MonthPartitionedTrades, TradePartsWithinMonth, SortedDateRanges, \
    CapitalGainLineAccumulator, CapitalGainLine, TradeCyclePerCompany, CapitalGainLinesPerCompany, CurrencyCompany, \
    get_year_month, Company, Currency


def print_month_partitioned_trades(month_partitioned_trades: MonthPartitionedTrades):
    print("MonthPartitionedTrades{")
    keys = sorted(month_partitioned_trades.keys())
    for key in keys:
        print(str(key) + " : " + str(month_partitioned_trades[key]))
    print("}")


def capital_gains_for_company(trade_cycle: TradeCycle, company: Company, currency: Currency) -> CapitalGainLines:
    capital_gain_line_accumulator = CapitalGainLineAccumulator(company, currency)
    sale_actions: QuantitatedTradeActions = trade_cycle.get(TradeType.SELL)
    buy_actions: QuantitatedTradeActions = trade_cycle.get(TradeType.BUY)
    if not sale_actions:
        raise ValueError("There are buys but no sell trades in the provided 'trade_actions' object!")
    if not buy_actions:
        raise ValueError("There are sells but no buy trades in the provided 'trade_actions' object!")

    sales_monthly_slices = split_by_months(sale_actions, TradeType.SELL)
    buys_monthly_slices = split_by_months(buy_actions, TradeType.BUY)
    capital_gain_lines: CapitalGainLines = []

    while len(sales_monthly_slices) > 0 and len(buys_monthly_slices) > 0:
        sorted_sale_year_months: SortedDateRanges = sorted(sales_monthly_slices.keys())
        print("\nsales_monthly_slices:")
        print_month_partitioned_trades(sales_monthly_slices)
        sorted_buy_year_months: SortedDateRanges = sorted(buys_monthly_slices.keys())
        print("\nbuys_monthly_slices:")
        print_month_partitioned_trades(buys_monthly_slices)

        # for sale_year_month in sorted_sale_year_months:
        sale_year_month = sorted_sale_year_months[0]
        # for buy_year_month in sorted_buy_year_months:
        buy_year_month = sorted_buy_year_months[0]

        sale_actions: TradePartsWithinMonth = sales_monthly_slices[sale_year_month]
        print("sale_actions")
        print(sale_actions)

        buy_actions: TradePartsWithinMonth = buys_monthly_slices[buy_year_month]
        print("buy_actions")
        print(buy_actions)

        target_quantity: Decimal = min(buy_actions.quantity(), sale_actions.quantity())
        sale_quantity_left = target_quantity
        buy_quantity_left = target_quantity
        iteration_count = 0
        while sale_actions.quantity() > 0 and buy_actions.quantity() > 0:
            print("\ncapital_gain_line aggregation cycle (" + str(iteration_count) + ")")
            iteration_count += 1

            extract_trades(sale_quantity_left, sale_actions, capital_gain_line_accumulator)
            extract_trades(buy_quantity_left, buy_actions, capital_gain_line_accumulator)
            print(capital_gain_line_accumulator)

            if sale_actions.count() == 0:
                # remove empty trades
                sales_monthly_slices.pop(sale_year_month)
            print("sales_monthly_slices")
            print_month_partitioned_trades(sales_monthly_slices)

            if buy_actions.count() == 0:
                # remove empty trades
                buys_monthly_slices.pop(buy_year_month)
            print("buys_monthly_slices")
            print_month_partitioned_trades(buys_monthly_slices)

        capital_gain_line: CapitalGainLine = capital_gain_line_accumulator.finalize()
        capital_gain_lines.append(capital_gain_line)

    print(capital_gain_lines)

    return capital_gain_lines


def extract_trades(quantity_left, trade_parts, capital_gain_line_accumulator):
    while quantity_left > 0:
        part = trade_parts.pop_trade_part()
        quantity_left -= part.quantity
        if quantity_left >= 0:
            capital_gain_line_accumulator.add_trade(part.quantity, part.action)
        else:
            capital_gain_line_accumulator.add_trade(part.quantity + quantity_left, part.action)
            trade_parts.push_trade_part(-quantity_left, part.action)
            quantity_left = 0


def split_by_months(actions: QuantitatedTradeActions, trade_type: TradeType) -> MonthPartitionedTrades:
    month_partitioned_trades: MonthPartitionedTrades = {}

    if not actions:
        return {}

    for quantitated_trade_action in actions:
        quantity: Decimal = quantitated_trade_action.quantity
        trade_action: TradeAction = quantitated_trade_action.action
        if trade_action.trade_type is not None and trade_action.trade_type != trade_type:
            raise ValueError("Incompatible trade types! Got " + trade_type.name + "for expected output and " +
                             trade_action.trade_type + " for the trade_action" + str(trade_action))
        year_month = get_year_month(trade_action.date_time)
        trades_within_month: TradePartsWithinMonth = month_partitioned_trades.get(year_month, TradePartsWithinMonth())
        print("pushing trade action " + str(trade_action))
        trades_within_month.push_trade_part(quantity, trade_action)
        month_partitioned_trades[year_month] = trades_within_month

    return month_partitioned_trades


def create_extract(trade_cycle_per_company: TradeCyclePerCompany, leftover: Union[str, os.PathLike[str]]) -> CapitalGainLinesPerCompany:
    capital_gain_lines_per_company: CapitalGainLinesPerCompany = {}
    leftover_trade_cycles_per_company: TradeCyclePerCompany = {}
    company_currency: CurrencyCompany
    for company_currency, trade_cycle in trade_cycle_per_company.items():
        currency = company_currency.currency
        company = company_currency.company
        trade_cycle.validate(currency, company)
        if not trade_cycle.has_sold() or not trade_cycle.has_bought():
            leftover_trade_cycles_per_company[company_currency] = trade_cycle
            continue
        capital_gain_lines: CapitalGainLines = capital_gains_for_company(trade_cycle, company, currency)
        capital_gain_lines_per_company[CurrencyCompany(currency, company)] = capital_gain_lines

    return capital_gain_lines_per_company
