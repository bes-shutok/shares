from decimal import Decimal

from domain import TradeType, TradeAction, TradeCycle, CapitalGainLines, QuantitatedTradeActions, \
    MonthPartitionedTrades, TradePartsWithinMonth, SortedDateRanges, \
    CapitalGainLineAccumulator, CapitalGainLine, TradeCyclePerCompany, CapitalGainLinesPerCompany, CurrencyCompany, \
    get_year_month, Company, Currency, QuantitatedTradeAction


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

    sales_monthly_slices: MonthPartitionedTrades = split_by_months(sale_actions, TradeType.SELL)
    print("\nsales_monthly_slices:")
    print_month_partitioned_trades(sales_monthly_slices)

    buys_monthly_slices: MonthPartitionedTrades = split_by_months(buy_actions, TradeType.BUY)
    print("\nbuys_monthly_slices:")
    print_month_partitioned_trades(buys_monthly_slices)

    capital_gain_lines: CapitalGainLines = []

    while len(sales_monthly_slices) > 0 and len(buys_monthly_slices) > 0:
        sorted_sale_year_months: SortedDateRanges = sorted(sales_monthly_slices.keys())
        sorted_buy_year_months: SortedDateRanges = sorted(buys_monthly_slices.keys())
        # for sale_year_month in sorted_sale_year_months:
        sale_year_month = sorted_sale_year_months[0]
        # for buy_year_month in sorted_buy_year_months:
        buy_year_month = sorted_buy_year_months[0]

        sale_trade_parts: TradePartsWithinMonth = sales_monthly_slices[sale_year_month]
        print("sale_trade_parts")
        print(sale_trade_parts)

        buy_trade_parts: TradePartsWithinMonth = buys_monthly_slices[buy_year_month]
        print("buy_trade_parts")
        print(buy_trade_parts)

        if buy_trade_parts.quantity() != sale_trade_parts.quantity():
            print(f"Buy quantity [{buy_trade_parts.quantity()}] != sale quantity [{sale_trade_parts.quantity()}]")
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

            if sale_trade_parts.quantity() == 0:
                # remove empty trades
                sales_monthly_slices.pop(sale_year_month)

            if buy_trade_parts.quantity() == 0:
                # remove empty trades
                buys_monthly_slices.pop(buy_year_month)

        capital_gain_line: CapitalGainLine = capital_gain_line_accumulator.finalize()
        capital_gain_lines.append(capital_gain_line)

    sale_actions.clear()
    if len(sales_monthly_slices) > 0:
        for trade_part in sales_monthly_slices.values():
            add_leftover(sale_actions, trade_part)
        print("Leftover sales_monthly_slices:")
        print_month_partitioned_trades(sales_monthly_slices)
        print(f"Leftover sale_actions: {sale_actions}")

    buy_actions.clear()
    if len(buys_monthly_slices) > 0:
        for trade_part in buys_monthly_slices.values():
            add_leftover(buy_actions, trade_part)
        print("Leftover buys_monthly_slices:")
        print_month_partitioned_trades(buys_monthly_slices)
        print(f"Leftover buy_actions: {buy_actions}")

    print(capital_gain_lines)

    return capital_gain_lines


def add_leftover(buy_actions: QuantitatedTradeActions, trade_part: TradePartsWithinMonth):
    total: Decimal = trade_part.quantity()
    for trade in trade_part.get_trades():
        if total == 0:
            raise ValueError("Total quantity is 0!")
        if trade.quantity > total:
            buy_actions.append(QuantitatedTradeAction(total, trade))
            total = Decimal(0)
        else:
            total -= trade.quantity
            buy_actions.append(QuantitatedTradeAction(trade.quantity, trade))


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


def calculate(trade_cycle_per_company: TradeCyclePerCompany, leftover_trades: TradeCyclePerCompany,
              capital_gains: CapitalGainLinesPerCompany):
    company_currency: CurrencyCompany
    trade_cycle: TradeCycle
    for company_currency, trade_cycle in trade_cycle_per_company.items():
        currency = company_currency.currency
        company = company_currency.company
        trade_cycle.validate(currency, company)
        if not trade_cycle.has_sold() or not trade_cycle.has_bought():
            leftover_trades[company_currency] = trade_cycle
            continue
        capital_gain_lines: CapitalGainLines = capital_gains_for_company(trade_cycle, company, currency)
        if not trade_cycle.is_empty():
            leftover_trades[company_currency] = trade_cycle
        capital_gains[CurrencyCompany(currency, company)] = capital_gain_lines
