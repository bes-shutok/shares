import csv
import os.path

from datetime import datetime
from enum import Enum
from decimal import Decimal


class TradeType(Enum):
    BUY = 1
    SELL = 2


work_dir: str = "E:\\tests"
source_file = "shares.csv"
source_path = os.path.join(work_dir, source_file)
result_file = "trades.csv"
result_path = os.path.join(work_dir, result_file)


class TradeAction:
    def __init__(self, symbol, date_time, currency, quantity, price, fee):
        # self.keys = ["time", "Quantity", "Price", "Fee"]
        self.symbol = symbol
        self.date_time = datetime.strptime(date_time, '%Y-%m-%d, %H:%M:%S')
        self.currency = currency
        if int(quantity) < 0:
            self.type = TradeType.SELL
            self.quantity = -int(quantity)
        else:
            self.type = TradeType.BUY
            self.quantity = int(quantity)

        self.price = Decimal(price)
        self.fee = Decimal(fee).copy_abs()

    def print(self):
        postfix = str(self.quantity) + " " + self.symbol + " shares" + " for " + \
                  str(self.price) + " " + self.currency + " at " + str(self.date_time) + " with fee " + \
                  str(self.fee) + " " + self.currency
        if self.type == TradeType.BUY:
            print("Bought " + postfix)
        else:
            print("Sold " + postfix)


def parse_data():
    print("This line will be printed.")
    print(source_path)

    trade_actions = {}
    share_trade_actions = []
    # open file in read mode
    with open(source_path, 'r') as read_obj:
        csv_dict_reader = csv.DictReader(read_obj)
        for row in csv_dict_reader:
            if row["Date/Time"] != "":
                key = row["Symbol"]
                if key in trade_actions.keys():
                    share_trade_actions = trade_actions[key]

                print(row["Currency"], row["Symbol"], row["Date/Time"], row["Quantity"], row["T. Price"],
                      row["Comm/Fee"])
                t = TradeAction(row["Symbol"], row["Date/Time"], row["Currency"], row["Quantity"], row["T. Price"],
                                row["Comm/Fee"])
                t.print()
                share_trade_actions.append(t)
                trade_actions[key] = share_trade_actions

    print(trade_actions)

    return trade_actions


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
    operation = "0.505060183*80/370"
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


def main():
    print("Starting conversion.")
    persist_data(parse_data())
    # test()


if __name__ == "__main__":
    main()
