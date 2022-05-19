import calendar
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Tuple, Optional


# noinspection DuplicatedCode
def get_ym_pair(date_time: datetime):
    return date_time.strftime("%Y"), date_time.strftime("%B")


class YearMonth:
    year: int
    month: int

    def __init__(self, date_time: datetime):
        self.year = date_time.year
        self.month = date_time.month

    def __repr__(self) -> str:
        return "[" + calendar.month_name[self.month] + ", " + str(self.year) + "]"

    # noinspection PyMethodMayBeStatic
    def __is_valid_operand(self, other) -> bool:
        return hasattr(other, "year") and hasattr(other, "month")

    def __eq__(self, other):
        if not self.__is_valid_operand(other):
            return NotImplemented
        return (self.year, self.month) == (other.year, other.month)

    def __lt__(self, other):
        if not self.__is_valid_operand(other):
            return NotImplemented
        return (self.year, self.month) < (other.year, other.month)

    def __hash__(self):
        return hash(self.__repr__())


# noinspection DuplicatedCode
def get_year_month(date_time: datetime) -> YearMonth:
    return YearMonth(date_time)


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

    def __repr__(self) -> str:
        postfix = str(self.quantity) + " " + self.symbol + " shares" + " for " + \
                  str(self.price) + " " + self.currency + " at " + str(self.date_time) + " with fee " + \
                  str(self.fee) + " " + self.currency
        if self.trade_type == TradeType.BUY:
            return "Bought " + postfix
        else:
            return "Sold " + postfix

    def print(self):
        postfix = str(self.quantity) + " " + self.symbol + " shares" + " for " + \
                  str(self.price) + " " + self.currency + " at " + str(self.date_time) + " with fee " + \
                  str(self.fee) + " " + self.currency
        if self.trade_type == TradeType.BUY:
            print("Bought " + postfix)
        else:
            print("Sold " + postfix)


TradeActionPart = Tuple[int, TradeAction]
TradeActionList = List[TradeActionPart]
TradeActions = Dict[TradeType, TradeActionList]
TradeActionsPerCompany = Dict[str, TradeActions]


class CapitalGainLine:
    __sell_date: YearMonth = None
    __sell_counts: List[int] = []
    __sell_trades: List[TradeAction] = []
    __buy_date: YearMonth = None
    __buy_counts: List[int] = []
    __buy_trades: List[TradeAction] = []

    def __init__(self, symbol: str, currency: str):
        self.symbol = symbol
        self.currency = currency

    def __repr__(self) -> str:
        return "CapitalGainLine{" + \
               "symbol:" + self.symbol + ", " \
                                         "currency:" + self.currency + ", \n" \
                                                                       "__sell_counts:" + str(
            self.__sell_counts) + ", \n" \
                                  "__sell_trades:" + str(self.__sell_trades) + ", \n" \
                                                                               "__buy_counts:" + str(
            self.__buy_counts) + ", \n" \
                                 "\n__buy_trades:" + str(self.__buy_trades) + \
               "\n}"

    def add_trade(self, count: int, ta: TradeAction):
        year_month = YearMonth(ta.date_time)
        if ta.trade_type == TradeType.SELL:
            if self.__sell_date is None:
                self.__sell_date = year_month
            else:
                if self.__sell_date != year_month:
                    raise ValueError("Incompatible dates in capital gain line add function! Expected ["
                                     + str(self.__sell_date) + "] " +
                                     " and got [" + str(year_month) + "]")
            self.__sell_counts.append(count)
            self.__sell_trades.append(ta)

        else:
            if self.__buy_date is None:
                self.__buy_date = year_month
            else:
                if self.__buy_date != year_month:
                    raise ValueError("Incompatible dates in capital gain line add function! Expected ["
                                     + str(self.__buy_date) + "] " + " and got ["
                                     + str(year_month) + "]")
            self.__buy_counts.append(count)
            self.__buy_trades.append(ta)

    def sold_quantity(self) -> int:
        return sum(self.__sell_counts)

    def bought_quantity(self) -> int:
        return sum(self.__buy_counts)

    def validate(self):
        if self.sold_quantity() != self.bought_quantity():
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


# Should we sort trades?
# todo
# Implement pop method to remove 1st or last element from the list of trades
class TradesWithinMonth:

    def __init__(self):
        self.symbol: Optional[str] = None
        self.currency: Optional[str] = None
        self.year_month: Optional[YearMonth] = None
        self.trade_type: Optional[TradeType] = None
        self.__quantities: Dict[datetime, int] = {}
        self.__trades: Dict[datetime, TradeAction] = {}

    def push_trade(self, quantity: int, ta: TradeAction):
        assert quantity > 0
        assert ta is not None
        if self.symbol is None:
            self.symbol = ta.symbol
            self.currency = ta.currency
            self.trade_type = ta.trade_type
            self.year_month = get_year_month(ta.date_time)

        if self.symbol == ta.symbol and self.currency == ta.currency \
                and self.trade_type == ta.trade_type and self.year_month == get_year_month(ta.date_time):
            self.__quantities[ta.date_time] = quantity
            self.__trades[ta.date_time] = ta
        else:
            raise ValueError("Incompatible trade_type or month in MonthlyTradeLine! Expected [" +
                             "[" + str(self.trade_type) + " and " + str(self.year_month) + "] " +
                             " and got [" + str(ta.trade_type) + " and " + str(self.year_month) + "]")

    def __earliest_date(self) -> datetime:
        return sorted(self.__quantities.keys())[0]

    def is_not_empty(self) -> bool:
        return self.count() > 0

    def get_top_count(self) -> int:
        date: datetime = self.__earliest_date()
        return self.__quantities[date]

    def pop_trade(self) -> TradeAction:
        date: datetime = self.__earliest_date()
        self.__quantities.pop(date)
        return self.__trades.pop(date)

    def quantity(self) -> int:
        return sum(self.__quantities.values())

    def count(self) -> int:
        return len(self.__quantities)

    def __repr__(self) -> str:
        return "TradesWithinMonth{" + "symbol:" + self.symbol + ", " "trade_type:" + str(self.trade_type) + ", " \
               + "currency:" + self.currency + ", " "year_month:" + str(self.year_month) + ", " + \
               "quantities:" + str(self.__quantities.values()) + ", " + \
               "\ntrades:" + str(self.__trades) + "}"

    def __eq__(self, other):
        return self.symbol == other.symbol and self.currency == other.currency and \
               self.year_month == other.year_month and self.trade_type == other.trade_type and \
               self.__quantities == other.__quantities and self.__trades == other.__trades


MonthPartitionedTrades = Dict[YearMonth, TradesWithinMonth]
SortedDateRanges = List[YearMonth]
PartitionedTradesByType = Dict[TradeType, MonthPartitionedTrades]
