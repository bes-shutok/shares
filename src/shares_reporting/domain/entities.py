from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, NamedTuple

from .value_objects import Currency, Company, TradeDate, get_trade_date, TradeType


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


@dataclass
class TradeCycle:
    bought: List[QuantitatedTradeAction] = field(default_factory=list)
    sold: List[QuantitatedTradeAction] = field(default_factory=list)

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

    def get(self, trade_type: TradeType) -> List[QuantitatedTradeAction]:
        if trade_type == TradeType.SELL:
            return self.sold
        return self.bought

    def is_empty(self) -> bool:
        return not (self.has_bought() or self.has_sold())


class CurrencyCompany(NamedTuple):
    currency: Currency
    company: Company


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