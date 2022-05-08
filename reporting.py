import copy
import csv
import os.path

from trade_classes import TradeType, TradeAction, TradeActions, TradeActionsPerCompany, TradeActionList
from datetime import datetime
from decimal import Decimal

work_dir: str = "E:\\tests"
source_file = "shares.csv"
source_path = os.path.join(work_dir, source_file)
result_file = "trades.csv"
result_path = os.path.join(work_dir, result_file)


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
        self.trade_type = ta.type
        self.quantity = ta.quantity
        self.price = ta.price
        self.fee = ta.fee

    def add_trade(self, ta: TradeAction):
        if ta.type == self.trade_type:
            if self.year_month_pair == get_ym_pair(ta.date_time):
                self.trades.append(ta)
                self.quantity += ta.quantity
                self.price += ta.price
                self.fee += ta.fee
            else:
                print(
                    "Incompatible trade date! expected " + str(self.year_month_pair) + " and got " + str(ta.date_time))
        else:
            print("Incompatible trade type! expected " + str(self.trade_type) + " and got " + str(ta.type))

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
        if ta.type == TradeType.SELL:
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


def parse_data(path: object):
    print("This line will be printed.")
    print(path)

    companies = {}
    trade_actions_per_company: TradeActionsPerCompany = {}
    trade_actions: TradeActions = {}
    trade_action_list: TradeActionList = []
    # open file in read mode
    with open(path, 'r') as read_obj:
        csv_dict_reader = csv.DictReader(read_obj)
        for row in csv_dict_reader:
            if row["Date/Time"] != "":
                company = row["Symbol"]
                if company in trade_actions_per_company.keys():
                    trade_actions = trade_actions_per_company[company]

                t = TradeAction(company, row["Date/Time"], row["Currency"], row["Quantity"], row["T. Price"],
                                row["Comm/Fee"])
                if t.type in trade_actions:
                    trade_action_list = trade_actions[t.type]
                else:
                    trade_action_list = []
                trade_action_list.append((t.quantity, t))
                trade_actions[t.type] = trade_action_list
                trade_actions_per_company[company] = trade_actions

    for k, v in companies.items():
        print("Printing trades for " + k)
        v.print()
        #v.select_complete_trades()
        #v.sell_actions = {get_ym_pair(datetime.now()): TradeActionsPerMonth(
        #    TradeAction("test", "2022-06-02, 09:30:01", "test", -3, 3, 3))}
        #print("changed")
        #v.print()
        #v.select_complete_trades()

    return trade_actions_per_company


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
            if action.type == TradeType.SELL:
                sell_actions_by_month = sell_actions_by_year[action.year_month_pair.year]
                sell_actions = sell_actions_by_month[action.year_month_pair.year]
                sell_actions.append(action)
    return sell_actions_by_symbol


def main():
    print("Starting conversion.")
    trade_actions = parse_data(source_path)
    # sell_actions = get_sell_actions(trade_actions)
    # persist_data(trade_actions)
    # test()


if __name__ == "__main__":
    main()
