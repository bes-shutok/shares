from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Tuple, Optional, Union


class TradeType(Enum):
    BUY = 1
    SELL = 2


# noinspection DuplicatedCode
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

    def __eq__(self, other):
        return self.symbol == other.symbol and \
               self.date_time == other.date_time and \
               self.currency == other.currency and \
               self.quantity == other.quantity and \
               self.price == other.price and \
               self.fee == other.fee

    def print(self):
        postfix = str(self.quantity) + " " + self.symbol + " shares" + " for " + \
                  str(self.price) + " " + self.currency + " at " + str(self.date_time) + " with fee " + \
                  str(self.fee) + " " + self.currency
        if self.type == TradeType.BUY:
            print("Bought " + postfix)
        else:
            print("Sold " + postfix)


TradeActionList = List[Tuple[int, TradeAction]]
TradeActions = Dict[TradeType, TradeActionList]
TradeActionsPerCompany = Dict[str, TradeActions]
