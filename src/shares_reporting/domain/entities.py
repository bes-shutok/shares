"""Domain entities representing core business concepts."""

from dataclasses import dataclass, field

# Use datetime.UTC for Python 3.11+
from datetime import UTC, datetime
from decimal import Decimal
from typing import NamedTuple

from .constants import DECIMAL_ZERO
from .exceptions import DataValidationError
from .value_objects import Company, Currency, TradeDate, TradeType


@dataclass
class TradeAction:
    """Represents a single trade action (buy or sell)."""

    # Cannot use NamedTuple because we need to do some mutation in the init method
    company: Company
    date_time: datetime
    currency: Currency
    quantity: Decimal
    price: Decimal
    fee: Decimal
    trade_type: TradeType

    def __init__(  # noqa: PLR0913
        self,
        company: Company,
        date_time: str,
        currency: Currency,
        quantity: str,
        price: str,
        fee: str,
    ):
        """Initialize the TradeAction.

        Args:
            company: The company associated with the trade.
            date_time: Date and time of the trade.
            currency: Currency of the trade.
            quantity: Quantity traded (string format).
            price: Price per unit.
            fee: Commission or fee.
        """
        quantity = quantity.replace(",", "")
        self.company = company
        self.date_time = datetime.strptime(date_time, "%Y-%m-%d, %H:%M:%S").replace(tzinfo=UTC)
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
    """Associates a quantity with a specific trade action."""

    quantity: Decimal
    action: TradeAction


@dataclass
class TradeCycle:
    """Represents a cycle of buy and sell trades for a position."""

    bought: list[QuantitatedTradeAction] = field(default_factory=list)
    sold: list[QuantitatedTradeAction] = field(default_factory=list)

    def has_bought(self) -> bool:
        """Check if any buy trades exist in the cycle."""
        return len(self.bought) > 0

    def has_sold(self) -> bool:
        """Check if any sell trades exist in the cycle."""
        return len(self.sold) > 0

    def validate(self, currency: Currency, company: Company) -> bool:
        """Validate that all trades in the cycle match the given currency and company.

        Args:
            currency: Expected currency.
            company: Expected company.

        Returns:
            True if valid, False otherwise.
        """
        if self.has_sold():
            any_action = self.sold[0].action
            return any_action.currency == currency and any_action.company == company
        any_action = self.bought[0].action
        return any_action.currency == currency and any_action.company == company

    def has(self, trade_type: TradeType) -> bool:
        """Check if trades of a specific type exist."""
        if trade_type == TradeType.SELL:
            return self.has_sold()
        return self.has_bought()

    def get(self, trade_type: TradeType) -> list[QuantitatedTradeAction]:
        """Get the list of trades for a specific type."""
        if trade_type == TradeType.SELL:
            return self.sold
        return self.bought

    def is_empty(self) -> bool:
        """Check if the cycle contains no trades."""
        return not (self.has_bought() or self.has_sold())


class CurrencyCompany(NamedTuple):
    """Composite key handling currency and company pair."""

    currency: Currency
    company: Company


@dataclass
class CapitalGainLine:
    """Represents a calculated capital gain/loss line item for reporting."""

    ticker: str
    currency: Currency
    sell_date: TradeDate
    sell_quantities: list[Decimal]
    sell_trades: list[TradeAction]
    buy_date: TradeDate
    buy_quantities: list[Decimal]
    buy_trades: list[TradeAction]

    def get_ticker(self):
        return self.ticker

    def get_currency(self):
        return self.currency

    def sell_quantity(self) -> Decimal:
        """Calculate total quantity sold."""
        return sum(self.sell_quantities, DECIMAL_ZERO)

    def buy_quantity(self) -> Decimal:
        """Calculate total quantity bought."""
        return sum(self.buy_quantities, DECIMAL_ZERO)

    def validate(self):
        """Validate data consistency of the capital gain line.

        Raises:
            DataValidationError: If sell/buy quantities or counts mismatch.
        """
        if self.sell_quantity() != self.buy_quantity():
            raise DataValidationError(
                "Different counts for sales ["
                + str(self.sell_quantities)
                + "] "
                + " and buys ["
                + str(self.buy_quantities)
                + "] in capital gain line!"
            )
        if len(self.sell_quantities) != len(self.sell_trades):
            raise DataValidationError(
                "Different number of counts ["
                + str(len(self.sell_quantities))
                + "] "
                + " and trades ["
                + str(len(self.sell_trades))
                + "] for sales in capital gain line!"
            )
        if len(self.buy_quantities) != len(self.buy_trades):
            raise DataValidationError(
                "Different number of counts ["
                + str(len(self.buy_quantities))
                + "] "
                + " and trades ["
                + str(len(self.buy_trades))
                + "] for buys in capital gain line!"
            )

    def get_sell_date(self) -> TradeDate:
        """Get the date containing the sale action(s)."""
        return self.sell_date

    def get_buy_date(self) -> TradeDate:
        """Get the date containing the buy action(s)."""
        return self.buy_date

    def get_sell_amount(self) -> str:
        """Generate Excel formula string for sell amount calculation."""
        result = "0"
        for i in range(len(self.sell_quantities)):
            result += "+" + str(self.sell_quantities[i]) + "*" + str(self.sell_trades[i].price)
        return result

    def get_buy_amount(self) -> str:
        """Generate Excel formula string for buy amount calculation."""
        result = "0"
        for i in range(len(self.buy_quantities)):
            result += "+" + str(self.buy_quantities[i]) + "*" + str(self.buy_trades[i].price)
        return result

    def get_expense_amount(self) -> str:
        """Generate Excel formula string for expense allocation."""
        result = "0"
        for i in range(len(self.sell_quantities)):
            result += (
                "+"
                + str(self.sell_quantities[i])
                + "*"
                + str(self.sell_trades[i].fee)
                + "/"
                + str(self.sell_trades[i].quantity)
            )
        for i in range(len(self.buy_quantities)):
            result += (
                "+"
                + str(self.buy_quantities[i])
                + "*"
                + str(self.buy_trades[i].fee)
                + "/"
                + str(self.buy_trades[i].quantity)
            )

        return result


@dataclass
class DividendIncomePerSecurity:
    """Container for dividend income data per security for capital investment income reporting."""

    symbol: str
    isin: str
    country: str
    gross_amount: Decimal
    total_taxes: Decimal
    currency: Currency

    def get_net_amount(self) -> Decimal:
        """Calculate net dividend amount after taxes."""
        return self.gross_amount - self.total_taxes

    def validate(self) -> None:
        """Validate dividend income data consistency."""
        if self.gross_amount < 0:
            raise DataValidationError(f"Gross amount cannot be negative: {self.gross_amount}")
        if self.total_taxes < 0:
            raise DataValidationError(f"Total taxes cannot be negative: {self.total_taxes}")
        if self.total_taxes > self.gross_amount:
            raise DataValidationError(f"Taxes ({self.total_taxes}) cannot exceed gross amount ({self.gross_amount})")
        if not self.symbol:
            raise DataValidationError("Symbol cannot be empty")
        if not self.isin:
            raise DataValidationError("ISIN cannot be empty")
        if not self.country:
            raise DataValidationError("Country cannot be empty")
