import csv
from copy import copy
from os import PathLike
from pathlib import Path

from parsing import parse_data
from supplementary import TradeType, TradeAction, \
    TradeActions, CapitalGainLines, TradeActionList, get_year_month, MonthPartitionedTrades, \
    TradesWithinMonth, SortedDateRanges, CapitalGainLine
from datetime import datetime
from decimal import Decimal


# Create TradesWithinMonths with Dict sorted by YearMonth
# Check whether it has sell orders
# Start creating CapitalGainLines with the earliest sell.
# find the earliest buy for the sell.
# Create CapitalGainLine and modify TradesWithinMonths accordingly
# Repeat from 2nd step
def capital_gains(trade_actions: TradeActions, symbol: str) -> CapitalGainLines:
    sold_trades = trade_actions[TradeType.SELL]
    bought_trades = trade_actions[TradeType.BUY]
    if not sold_trades:
        return []
    if not bought_trades:
        raise ValueError("There are sells but no buy trades in the provided 'trade_actions' object!")

    sold_within_months = split_by_months(sold_trades, TradeType.SELL)
    sorted_sale_date_ranges: SortedDateRanges = sorted(sold_within_months.keys())
    print("\nsold_within_months:")
    for sale_date_range in sorted_sale_date_ranges:
        print(str(sale_date_range) + ": " + str(sold_within_months[sale_date_range]))

    bought_within_months = split_by_months(bought_trades, TradeType.BUY)
    sorted_bought_date_ranges: SortedDateRanges = sorted(bought_within_months.keys())
    print("\nbought_within_months:")
    for bought_date_range in sorted_bought_date_ranges:
        print(str(bought_date_range) + ": " + str(bought_within_months[bought_date_range]))

    capital_gain_lines: CapitalGainLines = []
    trades_within_months: MonthPartitionedTrades

    #for sale_date_range in sorted_sale_date_ranges:
    sale_date_range = sorted_sale_date_ranges[0]
    #for bought_date_range in sorted_bought_date_ranges:
    bought_date_range = sorted_bought_date_ranges[0]
    sold_trades: TradesWithinMonth = sold_within_months[sale_date_range]
    print("sold_trades")
    print(sold_trades)
    bought_trades: TradesWithinMonth = bought_within_months[bought_date_range]
    print("bought_trades")
    print(bought_trades)
    sold_count: int = sold_trades.quantity()
    bought_count: int = bought_trades.quantity()
    left_count: int = sold_count
    capital_gain_line = CapitalGainLine(sold_trades.symbol, sold_trades.currency)
    while sold_trades.quantity() >= bought_trades.quantity() > 0:
        sold = sold_trades.pop_trade()
        bought = bought_trades.pop_trade()
        capital_gain_line.add_trade(sold.quantity, sold)
        capital_gain_line.add_trade(bought.quantity, bought)
    #if sold_count <= bought_count:
    #    capital_gain_line = CapitalGainLine(sold_trades.symbol, sold_trades.currency)
#
    #    while sold_trades.count() > 0:
    #        sold = sold_trades.pop_trade()
    #        capital_gain_line.add_trade(sold.quantity, sold)
    #    while bought_trades.get_top_count() <= left_count:
    #        left_count -= bought_trades.quantities[0]
    #        capital_gain_line.add_trade(bought_trades.quantities[0], bought_trades.trades[0])
#
    #    for i in range(len(sold_trades.quantities)):
    #        pass
    #    capital_gain_lines.append(capital_gain_line)

    print("capital_gain_lines")
    print(capital_gain_lines)
    # todo

    return []


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


# Get minimal pairs on individual trades level starting with the biggest sale quantity
def atomic_trade_gains(trade_actions: TradeActions) -> CapitalGainLines:
    capital_gain_lines: CapitalGainLines = []
    for trade_type, trade_actions in trade_actions:
        print("creating trade pairs")
    return None


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


# noinspection DuplicatedCode
class AllTradesPerCompany:
    sell_actions: dict[tuple[str, str], TradeActionsPerMonth] = {}
    buy_actions: dict[tuple[str, str], TradeActionsPerMonth] = {}
    complete_trades: dict[tuple[str, str, str, str], tuple[TradeActionsPerMonth, TradeActionsPerMonth]] = {}
    sell_actions_copy: dict[tuple[str, str], TradeActionsPerMonth] = None
    buy_actions_copy: dict[tuple[str, str], TradeActionsPerMonth] = None

    def __init__(self, symbol):
        self.symbol = symbol

    def add_trade(self, ta: TradeAction):
        year_month = get_ym_pair(ta.date_time)
        if ta.trade_type == TradeType.SELL:
            if year_month in self.sell_actions.keys():
                self.sell_actions[year_month].add_trade(ta)
            else:
                self.sell_actions.update({year_month: TradeActionsPerMonth(ta)})
        else:
            if year_month in self.buy_actions.keys():
                self.buy_actions[year_month].add_trade(ta)
            else:
                self.buy_actions.update({year_month: TradeActionsPerMonth(ta)})

    def select_complete_trades(self):
        print("\nTest\n")
        if self.sell_actions_copy is None:
            print("CREATING NEW COPY!!!!!!!!!!!")
            self.sell_actions_copy = self.sell_actions.copy()
            self.buy_actions_copy = self.buy_actions.copy()
            # self.sell_actions_copy = copy.deepcopy(self.sell_actions)

            for sell_dates, sell_actions in self.sell_actions_copy.items():
                for buy_dates, buy_actions in self.buy_actions_copy.items():
                    if sell_actions.year_month_pair > buy_actions.year_month_pair:
                        if sell_actions.quantity <= buy_actions.quantity:
                            self.complete_trades.update({sell_dates + buy_dates, (sell_actions, buy_actions)})

        for k, v in self.sell_actions_copy.items():
            print("For " + str(k))
            v.print()
        return None

    def print(self):
        print("The company " + self.symbol + " has the following sell trades: ")
        for k, v in self.sell_actions.items():
            print("For " + str(k))
            v.print()
        print("The company " + self.symbol + " has the following buy trades: ")
        for k, v in self.buy_actions.items():
            print("For " + str(k))
            v.print()


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
    trade_actions = parse_data(Path('resources', 'shares.csv'))
    capital_gains(trade_actions["BTU"], "BTU")
    # sell_actions = get_sell_actions(trade_actions)
    # persist_data(trade_actions)
    # test()


if __name__ == "__main__":
    main()
