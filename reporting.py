import csv
import os.path
from datetime import datetime

from enum import Enum


class TradeType(Enum):
    BUY = 1
    SELL = 2


class TradeAction:
    def __init__(self, symbol, date, currency, quantity, price, fee):
        self.symbol = symbol
        print(datetime.strptime(date, '%Y-%m-%d, %H:%M:%S'))
        self.date = datetime.strptime(date, '%Y-%m-%d, %H:%M:%S')
        self.currency = currency
        if int(quantity) < 0:
            self.type = TradeType.SELL
            self.quantity = -int(quantity)
        else:
            self.type = TradeType.BUY
            self.quantity = int(quantity)

        self.price = price
        self.fee = fee

    def print(self):
        if self.type == TradeType.BUY:
            print("Bought " + str(self.quantity) + " " + self.symbol + " shares" + " for " +
                  self.price + " " + self.currency + " at " + str(self.date))
        else:
            print("Sold " + str(self.quantity) + " " + self.symbol + " shares" + " for " +
                  self.price + " " + self.currency + " at " + str(self.date))


print("This line will be printed.")
work_dir = 'E:\\tests'
source_file = 'shares.csv'
source_path = os.path.join(work_dir, source_file)
print(source_path)
result_file = 'trades.csv'
result_path = os.path.join(work_dir, result_file)
print(result_path)

trades = {}
share_trades = []
# open file in read mode
with open(source_path, 'r') as read_obj:
    csv_dict_reader = csv.DictReader(read_obj)
    for row in csv_dict_reader:
        key = row['Symbol']
        if key in trades.keys():
            share_trades = trades[row['Symbol']]
        share_trades.append(
            {'time': row['Date/Time'], 'Quantity': row['Quantity'], 'Price': row['T. Price'], 'Fee': row['Comm/Fee']})
        if row['Date/Time'] != "":
            t = TradeAction(row['Symbol'], row['Date/Time'], row['Currency'], row['Quantity'], row['T. Price'], row['Comm/Fee'])
            t.print()
        trades[row['Symbol']] = share_trades
        print(row['Currency'], row['Symbol'], row['Date/Time'], row['Quantity'], row['T. Price'], row['Comm/Fee'])

print(trades)

with open(result_path, "w+", newline='', encoding='utf-8') as csv_file:
    csv_columns = ['time', 'Quantity', 'Price', 'Fee']
    writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
    writer.writeheader()
    for k, v in trades.items():
        writer.writerows(v)

csv_file.close()


def main():
    print("Hello world")
