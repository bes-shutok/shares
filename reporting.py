import csv
from pathlib import Path

from parsing import parse_data
from supplementary import TradeType, TradeAction, \
    TradeActions, CapitalGainLines, TradeActionList, get_year_month, MonthPartitionedTrades, \
    TradePartsWithinMonth, SortedDateRanges, CapitalGainLineAccumulator, TradeActionsPerCompany, \
    print_month_partitioned_trades, CapitalGainLine
from datetime import datetime
from decimal import Decimal


# Create TradesWithinMonths with Dict sorted by YearMonth
# Check whether it has sell orders
# Start creating CapitalGainLines with the earliest sell.
# find the earliest buy for the sell.
# Create CapitalGainLine and modify TradesWithinMonths accordingly
# Repeat from 2nd step
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

        target_quantity: int = min(buy_trade_parts.quantity(), sale_trade_parts.quantity())
        sale_quantity_left = target_quantity
        buy_quantity_left = target_quantity
        iteration_count = 0
        while sale_quantity_left > 0 and buy_quantity_left > 0:
            print("\ncapital_gain_line aggregation cycle (" + str(iteration_count) + ")")
            iteration_count += 1

            sale_part = sale_trade_parts.pop_trade_part()
            sale_quantity_left -= sale_part[0]
            buy_part = buy_trade_parts.pop_trade_part()
            buy_quantity_left -= buy_part[0]
            if sale_quantity_left >= 0:
                capital_gain_line_accumulator.add_trade(sale_part[0], sale_part[1])
            else:
                capital_gain_line_accumulator.add_trade(sale_part[0] + sale_quantity_left, sale_part[1])
                sale_trade_parts.push_trade_part(-sale_quantity_left, sale_part[1])
            if buy_quantity_left >= 0:
                capital_gain_line_accumulator.add_trade(buy_part[0], buy_part[1])
            else:
                capital_gain_line_accumulator.add_trade(buy_part[0] + buy_quantity_left, buy_part[1])
                buy_trade_parts.push_trade_part(-buy_quantity_left, buy_part[1])

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


def split_by_months(actions: TradeActionList, trade_type: TradeType) -> MonthPartitionedTrades:
    month_partitioned_trades: MonthPartitionedTrades = {}

    if not actions:
        return {}

    for trade_action_part in actions:
        quantity: int = trade_action_part[0]
        trade_action: TradeAction = trade_action_part[1]
        if trade_action.trade_type is not None and trade_action.trade_type != trade_type:
            raise ValueError("Incompatible trade types! Got " + str(trade_type) + "for expected output and " +
                             trade_action.trade_type + " for the trade_action" + str(trade_action))
        year_month = get_year_month(trade_action.date_time)
        trades_within_month: TradePartsWithinMonth = month_partitioned_trades.get(year_month, TradePartsWithinMonth())
        trades_within_month.push_trade_part(quantity, trade_action)
        month_partitioned_trades[year_month] = trades_within_month

    return month_partitioned_trades


work_dir: str = "E:\\tests"
source_file = "shares.csv"
source_path = Path(work_dir, source_file)
result_file = "trades.csv"
result_path = Path(work_dir, result_file)


def persist_data(trade_actions: {}):
    print(result_path)
    trades = {}
    for k, v in trade_actions.items():
        actions = trade_actions[k]
        share_trades = []
        for action in actions:
            share_trades.append({"time": action.date_time.date(), "Quantity": str(action.quantity),
                                 "Price": action.price, "Fee": action.fee})
        trades[k] = share_trades

    with open(result_path, 'w+', newline='', encoding='utf-8') as csv_file:
        csv_columns = ["time", "Quantity", "Price", "Fee"]
        writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
        writer.writeheader()
        for k, v in trades.items():
            writer.writerows(v)

    csv_file.close()


def vest_on():
    # operation 0.505060183*80/370

    number = "0.505060183"
    fee_float = float(number)
    fee_decimal = Decimal(number)
    fl = "Float representation: "
    dl = "Decimal representation: "
    print("/n")
    print(fl + str(fee_float))
    print(fl + str(fee_float * 80 / 370))
    print(dl + str(fee_decimal))
    print(dl + str(fee_decimal * 80 / 370))


def get_sell_actions(trade_actions):
    print("Get sell actions")
    sell_actions_by_symbol = {}
    sell_actions_by_year = {}
    for k, v in trade_actions.items():
        for action in v:
            action.print()
            if action.trade_type == TradeType.SELL:
                sell_actions_by_month = sell_actions_by_year[action.year_month_pair.year]
                sell_actions = sell_actions_by_month[action.year_month_pair.year]
                sell_actions.append(action)
    return sell_actions_by_symbol


def main():
    print("Starting conversion.")
    trade_actions: TradeActionsPerCompany = parse_data(Path('resources', 'shares.csv'))
    for symbol, trade_action_list in trade_actions.items():
        trade_action: TradeAction = trade_action_list[TradeType.SELL][0][1]
        assert symbol == trade_action.symbol
        currency = trade_action.currency
        capital_gains_for_company(trade_action_list, symbol, currency)
    # sell_actions = get_sell_actions(trade_actions)
    # persist_data(trade_actions)
    # test()


if __name__ == "__main__":
    main()
