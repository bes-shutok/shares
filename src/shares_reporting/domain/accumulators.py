from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from .entities import TradeAction, CapitalGainLine, QuantitatedTradeAction
from .value_objects import Company, Currency, TradeDate, get_trade_date, TradeType


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
                             str(self.trade_type) + " " + str(self.quantity()) + " and " + str(self.trade_date) + "] " +
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