import csv
from pathlib import Path

from parsing import parse_data
from supplementary import TradeType, TradeAction, \
    TradeActions, CapitalGainLines, TradeActionList, get_year_month, MonthPartitionedTrades, \
    TradesWithinMonth, SortedDateRanges, CapitalGainLineAccumulator, TradeActionsPerCompany, \
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
    sold_trades: TradeActionList = trade_actions[TradeType.SELL]
    bought_trades: TradeActionList = trade_actions[TradeType.BUY]
    if not sold_trades:
        return []
    if not bought_trades:
        raise ValueError("There are sells but no buy trades in the provided 'trade_actions' object!")

    sold_within_months = split_by_months(sold_trades, TradeType.SELL)
    bought_within_months = split_by_months(bought_trades, TradeType.BUY)
    capital_gain_lines: CapitalGainLines = []

    while len(sold_within_months) > 0 and len(bought_within_months) > 0:
        sorted_sale_date_ranges: SortedDateRanges = sorted(sold_within_months.keys())
        print("\nsold_within_months:")
        print_month_partitioned_trades(sold_within_months)
        sorted_bought_date_ranges: SortedDateRanges = sorted(bought_within_months.keys())
        print("\nbought_within_months:")
        print_month_partitioned_trades(bought_within_months)

        # for sale_date_range in sorted_sale_date_ranges:
        sale_date_range = sorted_sale_date_ranges[0]
        # for bought_date_range in sorted_bought_date_ranges:
        bought_date_range = sorted_bought_date_ranges[0]
        sold_trades: TradesWithinMonth = sold_within_months[sale_date_range]
        print("sold_trades")
        print(sold_trades)
        bought_trades: TradesWithinMonth = bought_within_months[bought_date_range]
        print("bought_trades")
        print(bought_trades)
        target_quantity: int = min(bought_trades.quantity(), sold_trades.quantity())
        sold_quantity_left = target_quantity
        bought_quantity_left = target_quantity
        iteration_count = 0
        while sold_trades.quantity() > 0 and bought_trades.quantity() > 0:
            print("\ncapital_gain_line aggregation cycle (" + str(iteration_count) + ")")
            iteration_count += 1

            sold = sold_trades.pop_trade()
            sold_quantity_left -= sold.quantity
            bought = bought_trades.pop_trade()
            bought_quantity_left -= bought.quantity
            if sold_quantity_left >= 0:
                capital_gain_line_accumulator.add_trade(sold.quantity, sold)
            else:
                capital_gain_line_accumulator.add_trade(sold.quantity + sold_quantity_left, sold)
                sold_trades.push_trade(-sold_quantity_left, sold)
            if bought_quantity_left >= 0:
                capital_gain_line_accumulator.add_trade(bought.quantity, bought)
            else:
                capital_gain_line_accumulator.add_trade(bought.quantity + bought_quantity_left, bought)
                bought_trades.push_trade(-bought_quantity_left, bought)

            print(capital_gain_line_accumulator)

            if sold_trades.count() > 0:
                sold_within_months[sale_date_range] = sold_trades
            else:
                sold_within_months.pop(sale_date_range)
            print("sold_within_months")
            print_month_partitioned_trades(sold_within_months)

            if bought_trades.count() > 0:
                bought_within_months[bought_date_range] = bought_trades
            else:
                bought_within_months.pop(bought_date_range)
            print("bought_within_months")
            print_month_partitioned_trades(bought_within_months)

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
        trades_within_month: TradesWithinMonth = month_partitioned_trades.get(year_month, TradesWithinMonth())
        trades_within_month.push_trade(quantity, trade_action)
        month_partitioned_trades[year_month] = trades_within_month

    return month_partitioned_trades


work_dir: str = "E:\\tests"
source_file = "shares.csv"
source_path = Path(work_dir, source_file)
result_file = "trades.csv"
result_path = Path(work_dir, result_file)


# noinspection DuplicatedCode
def get_ym_pair(date_time: datetime):
    return date_time.strftime("%Y"), date_time.strftime("%B")


# noinspection DuplicatedCode
class TradeActionsPerMonth:
    def __init__(self, ta: TradeAction):
        self.trades = [ta]
        self.symbol = ta.symbol
        self.year_month_pair = get_ym_pair(ta.date_time)
        self.currency = ta.currency
        self.trade_type = ta.trade_type
        self.quantity = ta.quantity
        self.price = ta.price
        self.fee = ta.fee

    def add_trade(self, ta: TradeAction):
        if ta.trade_type == self.trade_type:
            if self.year_month_pair == get_ym_pair(ta.date_time):
                self.trades.append(ta)
                self.quantity += ta.quantity
                self.price += ta.price
                self.fee += ta.fee
            else:
                print(
                    "Incompatible trade date! expected " + str(self.year_month_pair) + " and got " + str(ta.date_time))
        else:
            print("Incompatible trade type! expected " + str(self.trade_type) + " and got " + str(ta.trade_type))

    def print(self):
        postfix = str(self.quantity) + " " + self.symbol + " shares" + " for " + \
                  str(self.price) + " " + self.currency + " at " + str(self.year_month_pair) + " with fee " + \
                  str(self.fee) + " " + self.currency + "\n" + "trades:"
        if self.trade_type == TradeType.BUY:
            print("\nBought " + postfix)
        else:
            print("\nSold " + postfix)
        for trade in self.trades:
            trade.print()


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


def vest_date():
    print("")
    date_time = "2021-05-18, 14:53:23"
    print("before: " + date_time)
    date = datetime.strptime(date_time, '%Y-%m-%d, %H:%M:%S')
    print("after: " + str(date))
    print(str(date.year) + "  " + str(date.month) + "  " + date.strftime("%Y") + "  " + date.strftime("%B"))
    print(str(get_ym_pair(date)))


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
