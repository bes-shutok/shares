import calendar
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, NamedTuple


class TradeDate(NamedTuple):
    year: int
    month: int
    day: int

    def get_month_name(self) -> str:
        return calendar.month_name[self.month]

    def __repr__(self) -> str:
        return "[" + str(self.day) + " " + calendar.month_name[self.month] + ", " + str(self.year) + "]"


def get_trade_date(date: datetime) -> TradeDate:
    return TradeDate(date.year, date.month, date.day)


class TradeType(Enum):
    BUY = 1
    SELL = 2


class Currency(NamedTuple):
    currency: str


def get_currency(currency: str) -> Currency:
    if (len(currency)) == 3:
        pass
    else:
        raise ValueError("Currency is expected to be a length of 3, instead got [" + currency + "]!")
    return Currency(currency.upper())


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


class QuantitatedTradeAction(NamedTuple):
    quantity: Decimal
    action: TradeAction


QuantitatedTradeActions = List[QuantitatedTradeAction]


@dataclass
class TradeCycle:
    bought: QuantitatedTradeActions = field(default_factory=list)
    sold: QuantitatedTradeActions = field(default_factory=list)

    def has_bought(self) -> bool:
        return len(self.bought) > 0

    def has_sold(self) -> bool:
        return len(self.sold) > 0

    def validate(self, currency: Currency, company: Company) -> bool:
        if self.has_sold():
            any_action = self.sold[0].action
            return any_action.currency == currency and any_action.company == company
        any_action = self.bought[0].action
        return any_action.currency == currency and any_action.company == company

    def has(self, trade_type: TradeType) -> bool:
        if trade_type == TradeType.SELL:
            return self.has_sold()
        return self.has_bought()

    def get(self, trade_type: TradeType) -> QuantitatedTradeActions:
        if trade_type == TradeType.SELL:
            return self.sold
        return self.bought

    def is_empty(self) -> bool:
        return not (self.has_bought() or self.has_sold())


class CurrencyCompany(NamedTuple):
    currency: Currency
    company: Company


TradeCyclePerCompany = Dict[CurrencyCompany, TradeCycle]


@dataclass
class CapitalGainLine:
    ticker: str
    currency: Currency
    sell_date: TradeDate
    sell_quantities: List[Decimal]
    sell_trades: List[TradeAction]
    buy_date: TradeDate
    buy_quantities: List[Decimal]
    buy_trades: List[TradeAction]

    def get_ticker(self):
        return self.ticker

    def get_currency(self):
        return self.currency

    def sell_quantity(self) -> Decimal:
        return sum(self.sell_quantities, Decimal('0'))

    def buy_quantity(self) -> Decimal:
        return sum(self.buy_quantities, Decimal('0'))

    def validate(self):
        if self.sell_quantity() != self.buy_quantity():
            raise ValueError("Different counts for sales ["
                             + str(self.sell_quantities) + "] " + " and buys [" +
                             str(self.buy_quantities) + "] in capital gain line!")
        if len(self.sell_quantities) != len(self.sell_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.sell_quantities)) + "] " + " and trades [" +
                             str(len(self.sell_trades)) + "] for sales in capital gain line!")
        if len(self.buy_quantities) != len(self.buy_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.buy_quantities)) + "] " + " and trades [" +
                             str(len(self.buy_trades)) + "] for buys in capital gain line!")

    def get_sell_date(self) -> TradeDate:
        return self.sell_date

    def get_buy_date(self) -> TradeDate:
        return self.buy_date

    def get_sell_amount(self) -> str:
        result = "0"
        for i in range(len(self.sell_quantities)):
            result += "+" + str(self.sell_quantities[i]) + "*" + str(self.sell_trades[i].price)
        return result

    def get_buy_amount(self) -> str:
        result = "0"
        for i in range(len(self.buy_quantities)):
            result += "+" + str(self.buy_quantities[i]) + "*" + str(self.buy_trades[i].price)
        return result

    def get_expense_amount(self) -> str:
        result = "0"
        for i in range(len(self.sell_quantities)):
            result += "+" + str(self.sell_quantities[i]) + "*" + str(self.sell_trades[i].fee) \
                      + "/" + str(self.sell_trades[i].quantity)
        for i in range(len(self.buy_quantities)):
            result += "+" + str(self.buy_quantities[i]) + "*" + str(self.buy_trades[i].fee) \
                      + "/" + str(self.buy_trades[i].quantity)

        return result


@dataclass
class CapitalGainLineAccumulator:
    company: Company
    currency: Currency
    sell_date: TradeDate = None
    sell_counts: List[Decimal] = field(default_factory=list)
    sell_trades: List[TradeAction] = field(default_factory=list)
    buy_date: TradeDate = None
    buy_counts: List[Decimal] = field(default_factory=list)
    buy_trades: List[TradeAction] = field(default_factory=list)

    def get_ticker(self):
        return self.company

    def get_currency(self):
        return self.currency

    def add_trade(self, count: Decimal, ta: TradeAction):
        trade_date = get_trade_date(ta.date_time)
        if ta.trade_type == TradeType.SELL:
            if self.sell_date is None:
                self.sell_date = trade_date
            else:
                if self.sell_date != trade_date:
                    raise ValueError("Incompatible dates in capital gain line add function! Expected ["
                                     + str(self.sell_date) + "] " +
                                     " and got [" + str(trade_date) + "]")
            self.sell_counts.append(count)
            self.sell_trades.append(ta)

        else:
            if self.buy_date is None:
                self.buy_date = trade_date
            else:
                if self.buy_date != trade_date:
                    raise ValueError("Incompatible dates in capital gain line add function! Expected ["
                                     + str(self.buy_date) + "] " + " and got ["
                                     + str(trade_date) + "]")
            self.buy_counts.append(count)
            self.buy_trades.append(ta)

    def sold_quantity(self) -> Decimal:
        return sum(self.sell_counts, Decimal('0'))

    def bought_quantity(self) -> Decimal:
        return sum(self.buy_counts, Decimal('0'))

    # noinspection PyTypeChecker
    def finalize(self) -> CapitalGainLine:
        self.validate()
        result = CapitalGainLine(self.company, self.currency,
                                 self.sell_date, self.sell_counts, self.sell_trades,
                                 self.buy_date, self.buy_counts, self.buy_trades)
        self.sell_date = None
        self.sell_counts = []
        self.sell_trades = []
        self.buy_date = None
        self.buy_counts = []
        self.buy_trades = []
        return result

    def validate(self):
        if self.sold_quantity() <= 0 or self.bought_quantity() <= 0:
            raise ValueError("Cannot finalize empty Accumulator object!")
        if self.sold_quantity() != self.bought_quantity():
            raise ValueError("Different counts for sales ["
                             + str(self.sell_counts) + "] " + " and buys [" + str(self.buy_counts) +
                             "] in capital gain line!")
        if len(self.sell_counts) != len(self.sell_trades):
            raise ValueError("Different number of counts ["
                             + str(len(self.sell_counts)) + "] " + " and trades [" + str(len(self.sell_trades)) +
                             "] for sales in capital gain line!")


CapitalGainLines = List[CapitalGainLine]
CapitalGainLinesPerCompany = Dict[CurrencyCompany, CapitalGainLines]
SortedDateRanges = List[TradeDate]


@dataclass
class TradePartsWithinDay:
    company: Company= None
    currency: Currency = None
    trade_date: TradeDate = None
    trade_type: TradeType = None
    dates: List[datetime] = field(default_factory=list)
    quantities: List[Decimal] = field(default_factory=list)
    trades: List[TradeAction] = field(default_factory=list)

    def push_trade_part(self, quantity: Decimal, ta: TradeAction):
        assert quantity > 0
        assert ta is not None
        if self.company is None:
            self.company = ta.company
            self.currency = ta.currency
            self.trade_type = ta.trade_type
            self.trade_date = get_trade_date(ta.date_time)

        if self.company == ta.company and self.currency == ta.currency \
                and self.trade_type == ta.trade_type and self.trade_date == get_trade_date(ta.date_time):
            self.dates.append(ta.date_time)
            self.quantities.append(quantity)
            self.trades.append(ta)
        else:
            print(str(quantity))
            raise ValueError("Incompatible trade_type or date in DailyTradeLine! Expected [" +
                             str(self.trade_type) + " " + str(self.quantity) + " and " + str(self.trade_date) + "] " +
                             " and got [" + str(ta.trade_type) + " and " + str(self.trade_date) + "]")

    def pop_trade_part(self) -> QuantitatedTradeAction:
        idx: int = self.__get_top_index()
        self.dates.pop(idx)
        return QuantitatedTradeAction(quantity=self.quantities.pop(idx), action=self.trades.pop(idx))

    def get_top_count(self) -> Decimal:
        idx: int = self.__get_top_index()
        return self.quantities[idx]

    def __get_top_index(self) -> int:
        return self.dates.index(self.__earliest_date())

    def __earliest_date(self) -> datetime:
        t = self.dates.copy()
        t.sort()
        return t[0]

    def is_not_empty(self) -> bool:
        return self.quantity() > 0

    def quantity(self) -> Decimal:
        return sum(self.quantities, Decimal('0'))

    def get_trades(self) -> List[TradeAction]:
        return self.trades

    def get_quantities(self) -> Decimal:
        return sum(self.quantities, Decimal('0'))


DayPartitionedTrades = Dict[TradeDate, TradePartsWithinDay]
PartitionedTradesByType = Dict[TradeType, DayPartitionedTrades]


class CurrencyToCoordinate(NamedTuple):
    currency: Currency
    coordinate: str


CurrencyToCoordinates = List[CurrencyToCoordinate]
