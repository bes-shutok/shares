"""Transformation layer for calculating capital gains from raw trade data."""

from decimal import Decimal

from shares_reporting.infrastructure.logging_config import create_module_logger

from ..domain.accumulators import CapitalGainLineAccumulator, TradePartsWithinDay
from ..domain.collections import (
    CapitalGainLines,
    CapitalGainLinesPerCompany,
    DayPartitionedTrades,
    QuantitatedTradeActions,
    SortedDateRanges,
    TradeCyclePerCompany,
)
from ..domain.constants import DECIMAL_ZERO, PLACEHOLDER_YEAR, ZERO_QUANTITY
from ..domain.entities import (
    CapitalGainLine,
    CurrencyCompany,
    QuantitatedTradeAction,
    TradeAction,
    TradeCycle,
)
from ..domain.exceptions import DataValidationError
from ..domain.value_objects import Company, Currency, TradeType, parse_trade_date


def _create_placeholder_buys(
    trade_cycle: TradeCycle,
    company: Company,
    currency: Currency,
) -> None:
    """Create placeholder buy transactions for sells without corresponding buys.

    This function generates synthetic buy transactions with year=PLACEHOLDER_YEAR with price=0
    to allow FIFO matching for securities sold without buy history. This handles cases
    where securities were purchased in previous years or the buy data is unavailable.

    The placeholder approach:
    - Date: PLACEHOLDER_YEAR-01-01 00:00:00 (ensures FIFO ordering - earliest possible)
    - Price: 0 (conservative - maximizes taxable capital gain)
    - Quantity: Matches total quantity sold
    - Fee: 0

    Args:
        trade_cycle: Trade cycle with sells but no buys
        company: Company entity for the security
        currency: Currency entity for the trades

    Note:
        Using price=0 means the entire sale proceeds will be treated as capital gain.
        This is a conservative tax approach. Users should review and adjust these
        entries if they have actual cost basis information.
    """
    logger = create_module_logger(__name__)

    # Calculate total quantity sold
    total_sold = sum((sold_trade.quantity for sold_trade in trade_cycle.sold), DECIMAL_ZERO)

    # Create placeholder buy action
    placeholder_date = f"{PLACEHOLDER_YEAR}-01-01, 00:00:00"
    placeholder_action = TradeAction(
        company=company.ticker,
        date_time=placeholder_date,
        currency=currency.currency,
        quantity=str(total_sold),
        price=DECIMAL_ZERO,
        fee=DECIMAL_ZERO,
    )

    # Add to trade cycle
    trade_cycle.bought.append(QuantitatedTradeAction(quantity=total_sold, action=placeholder_action))

    logger.debug(
        "Created placeholder buy for %s: quantity=%s, date=%d-01-01, price=0",
        company.ticker,
        total_sold,
        PLACEHOLDER_YEAR,
    )


def log_partitioned_trades(day_partitioned_trades: DayPartitionedTrades, label: str = "") -> None:
    """Log day partitioned trades for debugging purposes.

    Args:
        day_partitioned_trades: The trades to log
        label: Optional label for context
    """
    logger = create_module_logger(__name__)
    if label:
        logger.debug("%s - DayPartitionedTrades{{", label)
    else:
        logger.debug("DayPartitionedTrades{")

    keys = sorted(day_partitioned_trades.keys())
    for key in keys:
        logger.debug("  %s : %s", key, day_partitioned_trades[key])
    logger.debug("}")


def calculate_company_gains(  # noqa: PLR0915
    trade_cycle: TradeCycle, company: Company, currency: Currency
) -> CapitalGainLines:
    """Calculate capital gains for a specific company and currency.

    Args:
        trade_cycle: Trade cycle containing buy and sell actions
        company: Company entity
        currency: Currency entity

    Returns:
        List of capital gain lines
    """
    logger = create_module_logger(__name__)
    capital_gain_line_accumulator = CapitalGainLineAccumulator(company, currency)
    sale_actions: QuantitatedTradeActions = trade_cycle.get(TradeType.SELL)
    buy_actions: QuantitatedTradeActions = trade_cycle.get(TradeType.BUY)
    if not sale_actions:
        raise DataValidationError("There are buys but no sell trades in the provided 'trade_actions' object!")
    if not buy_actions:
        raise DataValidationError("There are sells but no buy trades in the provided 'trade_actions' object!")

    sales_daily_slices: DayPartitionedTrades = split_by_days(sale_actions, TradeType.SELL)
    logger.debug("sales_daily_slices:")
    log_partitioned_trades(sales_daily_slices, "sales_daily_slices")

    buys_daily_slices: DayPartitionedTrades = split_by_days(buy_actions, TradeType.BUY)
    logger.debug("buys_daily_slices:")
    log_partitioned_trades(buys_daily_slices, "buys_daily_slices")

    capital_gain_lines: CapitalGainLines = []

    while len(sales_daily_slices) > 0 and len(buys_daily_slices) > 0:
        sorted_sale_dates: SortedDateRanges = sorted(sales_daily_slices.keys())
        sorted_buy_dates: SortedDateRanges = sorted(buys_daily_slices.keys())
        # for sale_date in sorted_sale_dates:
        sale_date = sorted_sale_dates[0]
        # for buy_date in sorted_buy_dates:
        buy_date = sorted_buy_dates[0]

        sale_trade_parts: TradePartsWithinDay = sales_daily_slices[sale_date]
        logger.debug("sale_trade_parts")
        logger.debug(str(sale_trade_parts))

        buy_trade_parts: TradePartsWithinDay = buys_daily_slices[buy_date]
        logger.debug("buy_trade_parts")
        logger.debug(str(buy_trade_parts))

        if buy_trade_parts.quantity() != sale_trade_parts.quantity():
            logger.debug(
                "Buy quantity [%s] != sale quantity [%s]", buy_trade_parts.quantity(), sale_trade_parts.quantity()
            )
        target_quantity: Decimal = min(buy_trade_parts.quantity(), sale_trade_parts.quantity())
        sale_quantity_left = target_quantity
        buy_quantity_left = target_quantity
        iteration_count = ZERO_QUANTITY
        while sale_trade_parts.quantity() > 0 and buy_trade_parts.quantity() > 0:
            logger.debug("capital_gain_line aggregation cycle (%s)", iteration_count)
            iteration_count += 1

            allocate_to_gain_line(sale_quantity_left, sale_trade_parts, capital_gain_line_accumulator)
            allocate_to_gain_line(buy_quantity_left, buy_trade_parts, capital_gain_line_accumulator)
            logger.debug(str(capital_gain_line_accumulator))

            if sale_trade_parts.quantity() == DECIMAL_ZERO:
                # remove empty trades
                sales_daily_slices.pop(sale_date)

            if buy_trade_parts.quantity() == DECIMAL_ZERO:
                # remove empty trades
                buys_daily_slices.pop(buy_date)

        capital_gain_line: CapitalGainLine = capital_gain_line_accumulator.finalize()
        capital_gain_lines.append(capital_gain_line)

    sale_actions.clear()
    if len(sales_daily_slices) > 0:
        for trade_part in sales_daily_slices.values():
            redistribute_unmatched_trades(sale_actions, trade_part)
        logger.debug("Leftover sales_daily_slices:")
        log_partitioned_trades(sales_daily_slices, "Leftover sales_daily_slices")
        logger.debug("Leftover sale_actions: %s", sale_actions)

    buy_actions.clear()
    if len(buys_daily_slices) > 0:
        for trade_part in buys_daily_slices.values():
            redistribute_unmatched_trades(buy_actions, trade_part)
        logger.debug("Leftover buys_daily_slices:")
        log_partitioned_trades(buys_daily_slices, "Leftover buys_daily_slices")
        logger.debug("Leftover buy_actions: %s", buy_actions)

    logger.debug("Final capital_gain_lines: %s lines", len(capital_gain_lines))

    return capital_gain_lines


def redistribute_unmatched_trades(buy_actions: QuantitatedTradeActions, trade_part: TradePartsWithinDay) -> None:
    """Redistribute unmatched trade quantities after FIFO matching process.

    This function handles the remaining trade quantities that couldn't be matched
    during the FIFO algorithm execution. It ensures that all quantities are
    properly allocated to the correct trade actions.

    Args:
        buy_actions: List to append redistributed QuantitatedTradeAction objects
        trade_part: TradePartsWithinDay containing unmatched trades to redistribute
    """
    total: Decimal = trade_part.quantity()
    for trade in trade_part.get_trades():
        if total == DECIMAL_ZERO:
            raise DataValidationError("Total quantity is 0!")
        if trade.quantity > total:
            buy_actions.append(QuantitatedTradeAction(total, trade))
            total = DECIMAL_ZERO
        else:
            total -= trade.quantity
            buy_actions.append(QuantitatedTradeAction(trade.quantity, trade))


def allocate_to_gain_line(
    quantity_left: Decimal,
    trade_parts: TradePartsWithinDay,
    capital_gain_line_accumulator: CapitalGainLineAccumulator,
) -> None:
    """Allocate specific trade quantities to a capital gain calculation line.

    This function handles the allocation of trade quantities to capital gain lines,
    supporting partial matching scenarios where quantities don't align perfectly.
    It ensures that trades are properly split or combined to create accurate
    capital gain calculations.

    Args:
        quantity_left: Remaining quantity to allocate for this capital gain line
        trade_parts: Available trades to allocate from (FIFO-ordered)
        capital_gain_line_accumulator: Accumulator to receive allocated trades
    """
    while quantity_left > DECIMAL_ZERO:
        part = trade_parts.pop_trade_part()
        quantity_left -= part.quantity
        if quantity_left >= DECIMAL_ZERO:
            capital_gain_line_accumulator.add_trade(part.quantity, part.action)
        else:
            capital_gain_line_accumulator.add_trade(part.quantity + quantity_left, part.action)
            trade_parts.push_trade_part(-quantity_left, part.action)
            quantity_left = DECIMAL_ZERO


def split_by_days(actions: QuantitatedTradeActions, trade_type: TradeType) -> DayPartitionedTrades:
    """Split trade actions by day for FIFO matching.

    Args:
        actions: List of quantitated trade actions
        trade_type: Type of trades to process

    Returns:
        Dictionary mapping trade dates to trade parts within day
    """
    logger = create_module_logger(__name__)
    day_partitioned_trades: DayPartitionedTrades = {}

    if not actions:
        return {}

    for quantitated_trade_action in actions:
        quantity: Decimal = quantitated_trade_action.quantity
        trade_action: TradeAction = quantitated_trade_action.action
        if trade_action.trade_type is not None and trade_action.trade_type != trade_type:
            raise DataValidationError(
                "Incompatible trade types! Got "
                + trade_type.name
                + "for expected output and "
                + str(trade_action.trade_type)
                + " for the trade_action"
                + str(trade_action)
            )
        trade_date = parse_trade_date(trade_action.date_time)
        trades_within_day: TradePartsWithinDay = day_partitioned_trades.get(trade_date, TradePartsWithinDay())
        logger.debug("pushing trade action %s", trade_action)
        trades_within_day.push_trade_part(quantity, trade_action)
        day_partitioned_trades[trade_date] = trades_within_day

    return day_partitioned_trades


def calculate_fifo_gains(
    trade_cycle_per_company: TradeCyclePerCompany,
    leftover_trades: TradeCyclePerCompany,
    capital_gains: CapitalGainLinesPerCompany,
) -> None:
    """Calculate capital gains using FIFO (First In, First Out) matching algorithm for tax reporting.

    This is the core business logic function that implements Portuguese tax-compliant capital gains
    calculation by matching buy/sell transactions chronologically within daily time buckets.

    Algorithm Details:
    1. **Company-Level Processing**: Iterates through each company/currency combination
    2. **Trade Validation**: Ensures each trade cycle has both buy and sell actions
    3. **FIFO Matching**: Uses capital_gains_for_company() to implement:
       - Daily bucketing of trades (tax compliance requirement)
       - Chronological matching of earliest buys with earliest sells
       - Partial matching for quantities that don't align perfectly
       - State machine design using CapitalGainLineAccumulator
    4. **Result Separation**:
       - Matched pairs → capital_gains (ready for Excel report)
       - Unmatched trades → leftover_trades (saved to CSV for reconciliation)

    Tax Compliance Rationale:
    - **Daily Bucketing**: Required by Portuguese tax authorities for proper tax year allocation
    - **FIFO Method**: Standard accounting principle accepted for capital gains calculations
    - **Partial Matching**: Handles real-world scenarios where trade quantities don't match exactly

    Args:
        trade_cycle_per_company: Raw trade data from Interactive Brokers, grouped by company/currency
        leftover_trades: Output container for unmatched trades (modified in-place)
        capital_gains: Output container for calculated capital gain lines (modified in-place)

    Output Effects:
    - Populates capital_gains with CapitalGainLine objects ready for tax reporting
    - Populates leftover_trades with incomplete TradeCycle objects for reconciliation
    - Each CapitalGainLine contains matched buy/sell pairs with calculated gains/losses

    Example Workflow:
        Input: 3 buys (100, 50, 75 shares) and 2 sells (80, 120 shares)
        Process: FIFO matching with daily bucketing
        Output: 2 complete capital gain lines + 1 leftover buy (25 shares)
    """
    company_currency: CurrencyCompany
    trade_cycle: TradeCycle
    for company_currency, trade_cycle in trade_cycle_per_company.items():
        currency = company_currency.currency
        company = company_currency.company
        trade_cycle.validate(currency, company)

        # Handle sells without buys: create placeholder buy transactions
        if trade_cycle.has_sold() and not trade_cycle.has_bought():
            _create_placeholder_buys(trade_cycle, company, currency)
            module_logger = create_module_logger(__name__)
            module_logger.warning(
                "Created placeholder buy transactions for %s (sold without buy data)",
                company.ticker,
            )

        # Handle buys without sells: add to leftover
        if not trade_cycle.has_sold():
            leftover_trades[company_currency] = trade_cycle
            continue
        capital_gain_lines: CapitalGainLines = calculate_company_gains(trade_cycle, company, currency)
        if not trade_cycle.is_empty():
            leftover_trades[company_currency] = trade_cycle
        capital_gains[CurrencyCompany(currency, company)] = capital_gain_lines
