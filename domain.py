import calendar
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, NamedTuple


class YearMonth(NamedTuple):
    year: int
    month: int

    def get_month_name(self) -> str:
        return calendar.month_name[self.month]

    def __repr__(self) -> str:
        return "[" + calendar.month_name[self.month] + ", " + str(self.year) + "]"


def get_year_month(date: datetime) -> YearMonth:
    return YearMonth(date.year, date.month)


class TradeType(Enum):
    BUY = 1
    SELL = 2


class Currency(NamedTuple):
    symbol: str


def get_currency(symbol: str) -> Currency:
    if (len(symbol)) == 3:
        pass
    else:
        raise ValueError("Currency is expected to be a length of 3, instead got [" + symbol + "]!")
    return Currency(symbol.upper())


class Company(NamedTuple):
    ticker: str


def get_company(ticker: str) -> Company:
    if (len(ticker)) > 0:
        pass
    else:
        raise ValueError("Company is expected to be not empty, instead got empty string!")
    # Not just uppercase because IB sometimes use abridgements like TKAd (Thyssen-Krupp Ag deutsch?)
    return Company(ticker)


@dataclass
class TradeAction:
    # Cannot use NamedTuple because we need to do some mutation in the init method
    company: Company
    date_time: datetime
    currency: Currency
    quantity: Decimal
    price: Decimal
    fee: Decimal

    def __init__(self, company, date_time, currency, quantity: str, price, fee):
        quantity = quantity.replace(",", "")
        self.company = company
        self.date_time = datetime.strptime(date_time, '%Y-%m-%d, %H:%M:%S')
        self.currency = currency
        if Decimal(quantity) < 0:
            self.trade_type = TradeType.SELL
            self.quantity = -Decimal(quantity)
        else:
            self.trade_type = TradeType.BUY
            self.quantity = Decimal(quantity)

        self.price = Decimal(price)
        self.fee = Decimal(fee).copy_abs()


class TradeActionPart(NamedTuple):
    quantity: Decimal
    action: TradeAction


TradeActionList = List[TradeActionPart]
TradeActions = Dict[TradeType, TradeActionList]


class CurrencyCompany(NamedTuple):
    currency: Currency
    company: Company


TradeActionsPerCompany = Dict[CurrencyCompany, TradeActions]


@dataclass
class CapitalGainLine:
    __symbol: str
    __currency: Currency
    __sell_date: YearMonth
    __sell_quantities: List[Decimal]
    __sell_trades: List[TradeAction]
    __buy_date: YearMonth
    __buy_quantities: List[Decimal]
    __buy_trades: List[TradeAction]

    def get_symbol(self):
        return self.__symbol

    def get_currency(self):
        return self.__currency

    def sell_quantity(self) -> Decimal:
        return sum(self.__sell_quantities)

    def buy_quantity(self) -> Decimal:
        return sum(self.__buy_quantities)

    def validate(self):
        if self.sell_quantity() != self.buy_quantity():
            raise ValueError("Different counts for sales ["
                             + str(self.__sell_quantities) + "] " + " and buys [" +
                             str(self.__buy_quantities) + "] in capital gain line!")
        if len(self.__sell_quantities) != len(self.__sell_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.__sell_quantities)) + "] " + " and trades [" +
                             str(len(self.__sell_trades)) + "] for sales in capital gain line!")
        if len(self.__buy_quantities) != len(self.__buy_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.__buy_quantities)) + "] " + " and trades [" +
                             str(len(self.__buy_trades)) + "] for buys in capital gain line!")

    def get_sell_date(self) -> YearMonth:
        return self.__sell_date

    def get_buy_date(self) -> YearMonth:
        return self.__buy_date

    def get_sell_amount(self) -> str:
        result = "0"
        for i in range(len(self.__sell_quantities)):
            result += "+" + str(self.__sell_quantities[i]) + "*" + str(self.__sell_trades[i].price)
        return result

    def get_buy_amount(self) -> str:
        result = "0"
        for i in range(len(self.__buy_quantities)):
            result += "+" + str(self.__buy_quantities[i]) + "*" + str(self.__buy_trades[i].price)
        return result

    def get_expense_amount(self) -> str:
        result = "0"
        for i in range(len(self.__sell_quantities)):
            result += "+" + str(self.__sell_quantities[i]) + "*" + str(self.__sell_trades[i].fee) \
                      + "/" + str(self.__sell_trades[i].quantity)
        for i in range(len(self.__buy_quantities)):
            result += "+" + str(self.__buy_quantities[i]) + "*" + str(self.__buy_trades[i].fee) \
                      + "/" + str(self.__buy_trades[i].quantity)

        return result


@dataclass
class CapitalGainLineAccumulator:
    company: Company
    __currency: Currency
    __sell_date: YearMonth = None
    __sell_counts: List[Decimal] = field(default_factory=list)
    __sell_trades: List[TradeAction] = field(default_factory=list)
    __buy_date: YearMonth = None
    __buy_counts: List[Decimal] = field(default_factory=list)
    __buy_trades: List[TradeAction] = field(default_factory=list)

    def get_symbol(self):
        return self.company

    def get_currency(self):
        return self.__currency

    def add_trade(self, count: Decimal, ta: TradeAction):
        year_month = get_year_month(ta.date_time)
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

    def sold_quantity(self) -> Decimal:
        return sum(self.__sell_counts)

    def bought_quantity(self) -> Decimal:
        return sum(self.__buy_counts)

    # noinspection PyTypeChecker
    def finalize(self) -> CapitalGainLine:
        self.validate()
        result = CapitalGainLine(self.company, self.__currency,
                                 self.__sell_date, self.__sell_counts, self.__sell_trades,
                                 self.__buy_date, self.__buy_counts, self.__buy_trades)
        self.__sell_date = None
        self.__sell_counts = []
        self.__sell_trades = []
        self.__buy_date = None
        self.__buy_counts = []
        self.__buy_trades = []
        return result

    def validate(self):
        if self.sold_quantity() <= 0 or self.bought_quantity() <= 0:
            raise ValueError("Cannot finalize empty Accumulator object!")
        if self.sold_quantity() != self.bought_quantity():
            raise ValueError("Different counts for sales ["
                             + str(self.__sell_counts) + "] " + " and buys [" + str(self.__buy_counts) +
                             "] in capital gain line!")
        if len(self.__sell_counts) != len(self.__sell_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.__sell_counts)) + "] " + " and trades [" + str(len(self.__sell_trades)) +
                             "] for sales in capital gain line!")


CapitalGainLines = List[CapitalGainLine]
CapitalGainLinesPerCompany = Dict[CurrencyCompany, CapitalGainLines]
SortedDateRanges = List[YearMonth]


@dataclass
class TradePartsWithinMonth:
    company: Optional[Company] = None
    currency: Optional[Currency] = None
    year_month: Optional[YearMonth] = None
    trade_type: Optional[TradeType] = None
    __dates: List[datetime] = field(default_factory=list)
    __quantities: List[Decimal] = field(default_factory=list)
    __trades: List[TradeAction] = field(default_factory=list)

    def push_trade_part(self, quantity: Decimal, ta: TradeAction):
        assert quantity > 0
        assert ta is not None
        if self.company is None:
            self.company = ta.company
            self.currency = ta.currency
            self.trade_type = ta.trade_type
            self.year_month = get_year_month(ta.date_time)

        if self.company == ta.company and self.currency == ta.currency \
                and self.trade_type == ta.trade_type and self.year_month == get_year_month(ta.date_time):
            self.__dates.append(ta.date_time)
            self.__quantities.append(quantity)
            self.__trades.append(ta)
        else:
            print(str(quantity))
            raise ValueError("Incompatible trade_type or month in MonthlyTradeLine! Expected [" +
                             str(self.trade_type) + " " + str(self.quantity) + " and " + str(self.year_month) + "] " +
                             " and got [" + str(ta.trade_type) + " and " + str(self.year_month) + "]")

    def pop_trade_part(self) -> TradeActionPart:
        idx: int = self.__get_top_index()
        self.__dates.pop(idx)
        return TradeActionPart(quantity=self.__quantities.pop(idx), action=self.__trades.pop(idx))

    def get_top_count(self) -> Decimal:
        idx: int = self.__get_top_index()
        return self.__quantities[idx]

    def __get_top_index(self) -> int:
        return self.__dates.index(self.__earliest_date())

    def __earliest_date(self) -> datetime:
        t = self.__dates.copy()
        t.sort()
        return t[0]

    def is_not_empty(self) -> bool:
        return self.count() > 0

    def quantity(self) -> Decimal:
        return sum(self.__quantities)

    def count(self) -> int:
        return len(self.__quantities)


MonthPartitionedTrades = Dict[YearMonth, TradePartsWithinMonth]
PartitionedTradesByType = Dict[TradeType, MonthPartitionedTrades]


class CurrencyToCoordinate(NamedTuple):
    currency: Currency
    coordinate: str


CurrencyToCoordinates = List[CurrencyToCoordinate]
