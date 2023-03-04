from decimal import Decimal

from domain import TradeType, TradeAction, TradeActions, CapitalGainLines, TradeActionList, \
    MonthPartitionedTrades, TradePartsWithinMonth, SortedDateRanges, \
    CapitalGainLineAccumulator, CapitalGainLine, TradeActionsPerCompany, CapitalGainLinesPerCompany, CurrencyCompany, \
    get_year_month


def print_month_partitioned_trades(month_partitioned_trades: MonthPartitionedTrades):
    print("MonthPartitionedTrades{")
    keys = sorted(month_partitioned_trades.keys())
    for key in keys:
        print(str(key) + " : " + str(month_partitioned_trades[key]))
    print("}")


def capital_gains_for_company(trade_actions: TradeActions, symbol: str, currency: str) -> CapitalGainLines:
    capital_gain_line_accumulator = CapitalGainLineAccumulator(symbol, currency)
    sale_trade_parts: TradeActionList = trade_actions[TradeType.SELL]
    buy_trade_parts: TradeActionList = trade_actions[TradeType.BUY]
    if not sale_trade_parts:
        return []
    if not buy_trade_parts:
        raise ValueError("There are sells but no buy_part trades in the provided 'trade_actions' object!")

    sales_monthly_slices = split_by_months(sale_trade_parts, TradeType.SELL)
    buys_monthly_slices = split_by_months(buy_trade_parts, TradeType.BUY)
    capital_gain_lines: CapitalGainLines = []

    while len(sales_monthly_slices) > 0 and len(buys_monthly_slices) > 0:
        sorted_sale_dates_slices: SortedDateRanges = sorted(sales_monthly_slices.keys())
        print("\nsales_monthly_slices:")
        print_month_partitioned_trades(sales_monthly_slices)
        sorted_buy_dates_slices: SortedDateRanges = sorted(buys_monthly_slices.keys())
        print("\nbuys_monthly_slices:")
        print_month_partitioned_trades(buys_monthly_slices)

        # for sale_date in sorted_sale_dates_slices:
        sale_date = sorted_sale_dates_slices[0]
        # for buy_date in sorted_buy_dates_slices:
        buy_date = sorted_buy_dates_slices[0]

        sale_trade_parts: TradePartsWithinMonth = sales_monthly_slices[sale_date]
        print("sale_trade_parts")
        print(sale_trade_parts)

        buy_trade_parts: TradePartsWithinMonth = buys_monthly_slices[buy_date]
        print("buy_trade_parts")
        print(buy_trade_parts)

        target_quantity: Decimal = min(buy_trade_parts.quantity(), sale_trade_parts.quantity())
        sale_quantity_left = target_quantity
        buy_quantity_left = target_quantity
        iteration_count = 0
        while sale_trade_parts.quantity() > 0 and buy_trade_parts.quantity() > 0:
            print("\ncapital_gain_line aggregation cycle (" + str(iteration_count) + ")")
            iteration_count += 1

            extract_trades(sale_quantity_left, sale_trade_parts, capital_gain_line_accumulator)
            extract_trades(buy_quantity_left, buy_trade_parts, capital_gain_line_accumulator)
            print(capital_gain_line_accumulator)

            if sale_trade_parts.count() == 0:
                # remove empty trades
                sales_monthly_slices.pop(sale_date)
            print("sales_monthly_slices")
            print_month_partitioned_trades(sales_monthly_slices)

            if buy_trade_parts.count() == 0:
                # remove empty trades
                buys_monthly_slices.pop(buy_date)
            print("buys_monthly_slices")
            print_month_partitioned_trades(buys_monthly_slices)

        capital_gain_line: CapitalGainLine = capital_gain_line_accumulator.finalize()
        capital_gain_lines.append(capital_gain_line)

    print(capital_gain_lines)

    return capital_gain_lines


def extract_trades(quantity_left, trade_parts, capital_gain_line_accumulator):
    while quantity_left > 0:
        part = trade_parts.pop_trade_part()
        quantity_left -= part[0]
        if quantity_left >= 0:
            capital_gain_line_accumulator.add_trade(part[0], part[1])
        else:
            capital_gain_line_accumulator.add_trade(part[0] + quantity_left, part[1])
            trade_parts.push_trade_part(-quantity_left, part[1])
            quantity_left = 0


def split_by_months(actions: TradeActionList, trade_type: TradeType) -> MonthPartitionedTrades:
    month_partitioned_trades: MonthPartitionedTrades = {}

    if not actions:
        return {}

    for trade_action_part in actions:
        quantity: Decimal = trade_action_part[0]
        trade_action: TradeAction = trade_action_part[1]
        if trade_action.trade_type is not None and trade_action.trade_type != trade_type:
            raise ValueError("Incompatible trade types! Got " + str(trade_type) + "for expected output and " +
                             trade_action.trade_type + " for the trade_action" + str(trade_action))
        year_month = get_year_month(trade_action.date_time)
        trades_within_month: TradePartsWithinMonth = month_partitioned_trades.get(year_month, TradePartsWithinMonth())
        print("pushing trade action " + str(trade_action))
        trades_within_month.push_trade_part(quantity, trade_action)
        month_partitioned_trades[year_month] = trades_within_month

    return month_partitioned_trades


def create_extract(trade_actions_per_company: TradeActionsPerCompany) -> CapitalGainLinesPerCompany:
    capital_gain_lines_per_company: CapitalGainLinesPerCompany = {}
    for company_currency, trade_actions in trade_actions_per_company.items():
        currency = company_currency.currency
        symbol = company_currency.company
        if len(trade_actions) != 2:
            continue
        trade_action: TradeAction = trade_actions[TradeType.SELL][0][1]
        assert symbol == trade_action.symbol
        assert currency == trade_action.currency

        capital_gain_lines: CapitalGainLines = capital_gains_for_company(trade_actions, symbol, currency)
        capital_gain_lines_per_company[CurrencyCompany(currency, symbol)] = capital_gain_lines

    return capital_gain_lines_per_company
