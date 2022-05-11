from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Tuple


# noinspection DuplicatedCode
def get_ym_pair(date_time: datetime):
    return date_time.strftime("%Y"), date_time.strftime("%B")


class TradeType(Enum):
    BUY = 1
    SELL = 2


class TradeAction:
    def __init__(self, symbol, date_time, currency, quantity, price, fee):
        self.symbol = symbol
        self.date_time = datetime.strptime(date_time, '%Y-%m-%d, %H:%M:%S')
        self.currency = currency
        if int(quantity) < 0:
            self.trade_type = TradeType.SELL
            self.quantity = -int(quantity)
        else:
            self.trade_type = TradeType.BUY
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
        if self.trade_type == TradeType.BUY:
            print("Bought " + postfix)
        else:
            print("Sold " + postfix)


TradeActionList = List[Tuple[int, TradeAction]]
TradeActions = Dict[TradeType, TradeActionList]
TradeActionsPerCompany = Dict[str, TradeActions]


class CapitalGainLine:
    __sell_date: Tuple[str, str] = None
    __sell_counts: List[int] = []
    __sell_trades: List[TradeAction] = []
    __buy_date: Tuple[str, str] = None
    __buy_counts: List[int] = []
    __buy_trades: List[TradeAction] = []

    def __init__(self, symbol: str, currency: str):
        self.symbol = symbol
        self.currency = currency

    def add_trade(self, count: int, ta: TradeAction):
        year_month = get_ym_pair(ta.date_time)
        if ta.trade_type == TradeType.SELL:
            if self.__sell_date is None:
                self.__sell_date = year_month
            else:
                if self.__sell_date != year_month:
                    raise ValueError("Incompatible dates in capital gain line add function! Expected ["
                                     + str(self.__sell_date) + "] " + " and got [" + str(year_month) + "]")
            self.__sell_counts.append(count)
            self.__sell_trades.append(ta)

        else:
            if self.__buy_date is None:
                self.__buy_date = year_month
            else:
                if self.__buy_date != year_month:
                    raise ValueError("Incompatible dates in capital gain line add function! Expected ["
                                     + str(self.__buy_date) + "] " + " and got [" + str(year_month) + "]")
            self.__buy_counts.append(count)
            self.__buy_trades.append(ta)

    def validate(self):
        if sum(self.__sell_counts) != sum(self.__buy_counts):
            raise ValueError("Different counts for sales ["
                             + str(self.__sell_counts) + "] " + " and buys [" + str(self.__buy_counts) +
                             "] in capital gain line!")
        if len(self.__sell_counts) != len(self.__sell_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.__sell_counts)) + "] " + " and trades [" + str(len(self.__sell_trades)) +
                             "] for sales in capital gain line!")
        if len(self.__buy_counts) != len(self.__buy_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.__buy_counts)) + "] " + " and trades [" + str(len(self.__buy_trades)) +
                             "] for buys in capital gain line!")


CapitalGainLines = List[CapitalGainLine]
CapitalGainLinesPerCompany = Dict[str, CapitalGainLines]


class MonthlyTradeLine:
    quantities: List[int]
    trades: List[TradeAction]

    def __init__(self, symbol: str, currency: str, trade_type: TradeType, month: Tuple[str, str]):
        self.symbol = symbol
        self.currency = currency
        self.trade_type = trade_type
        self.month = month

    def add_trade(self, quantity: int, month: Tuple[str, str], ta: TradeAction):
        assert quantity > 0
        assert month is not None
        assert ta is not None

        if self.trade_type == ta.trade_type and self.month == month:
            self.quantities.append(quantity)
            self.trades.append(ta)
        else:
            raise ValueError("Incompatible trade_type or month in MonthlyTradeLine! Expected [" +
                             "[" + str(self.trade_type) + " and " + str(self.month) + "] " +
                             " and got [" + str(ta.trade_type) + " and " + str(month) + "]")

    def quantity(self) -> int:
        return sum(self.quantities)


MonthlyTradeLines = Dict[TradeType, List[MonthlyTradeLine]]
