from decimal import Decimal

from ..domain.collections import (
    CapitalGainLines,
    CapitalGainLinesPerCompany,
    DayPartitionedTrades,
    QuantitatedTradeActions,
    SortedDateRanges,
    TradeCyclePerCompany,
)
from ..domain.entities import (
    TradeAction,
    TradeCycle,
    CapitalGainLine,
    CurrencyCompany,
    QuantitatedTradeAction,
)
from ..domain.value_objects import TradeType, get_trade_date, Company, Currency
from ..domain.accumulators import TradePartsWithinDay, CapitalGainLineAccumulator
from ..domain.exceptions import CapitalGainsCalculationError, DataValidationError
from ..infrastructure.logging_config import get_logger


def log_day_partitioned_trades(
    day_partitioned_trades: DayPartitionedTrades, label: str = ""
) -> None:
    """
    Log day partitioned trades for debugging purposes.

    Args:
        day_partitioned_trades: The trades to log
        label: Optional label for context
    """
    logger = get_logger(__name__)
    if label:
        logger.debug(f"{label} - DayPartitionedTrades{{")
    else:
        logger.debug("DayPartitionedTrades{")

    keys = sorted(day_partitioned_trades.keys())
    for key in keys:
        logger.debug(f"  {key} : {day_partitioned_trades[key]}")
    logger.debug("}")


def capital_gains_for_company(
    trade_cycle: TradeCycle, company: Company, currency: Currency
) -> CapitalGainLines:
    """
    Calculate capital gains for a specific company and currency.

    Args:
        trade_cycle: Trade cycle containing buy and sell actions
        company: Company entity
        currency: Currency entity

    Returns:
        List of capital gain lines
    """
    logger = get_logger(__name__)
    capital_gain_line_accumulator = CapitalGainLineAccumulator(company, currency)
    sale_actions: QuantitatedTradeActions = trade_cycle.get(TradeType.SELL)
    buy_actions: QuantitatedTradeActions = trade_cycle.get(TradeType.BUY)
    if not sale_actions:
        raise DataValidationError(
            "There are buys but no sell trades in the provided 'trade_actions' object!"
        )
    if not buy_actions:
        raise DataValidationError(
            "There are sells but no buy trades in the provided 'trade_actions' object!"
        )

    sales_daily_slices: DayPartitionedTrades = split_by_days(sale_actions, TradeType.SELL)
    logger.debug("sales_daily_slices:")
    log_day_partitioned_trades(sales_daily_slices, "sales_daily_slices")

    buys_daily_slices: DayPartitionedTrades = split_by_days(buy_actions, TradeType.BUY)
    logger.debug("buys_daily_slices:")
    log_day_partitioned_trades(buys_daily_slices, "buys_daily_slices")

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
                f"Buy quantity [{buy_trade_parts.quantity()}] != sale quantity [{sale_trade_parts.quantity()}]"
            )
        target_quantity: Decimal = min(buy_trade_parts.quantity(), sale_trade_parts.quantity())
        sale_quantity_left = target_quantity
        buy_quantity_left = target_quantity
        iteration_count = 0
        while sale_trade_parts.quantity() > 0 and buy_trade_parts.quantity() > 0:
            logger.debug(f"capital_gain_line aggregation cycle ({iteration_count})")
            iteration_count += 1

            extract_trades(sale_quantity_left, sale_trade_parts, capital_gain_line_accumulator)
            extract_trades(buy_quantity_left, buy_trade_parts, capital_gain_line_accumulator)
            logger.debug(str(capital_gain_line_accumulator))

            if sale_trade_parts.quantity() == 0:
                # remove empty trades
                sales_daily_slices.pop(sale_date)

            if buy_trade_parts.quantity() == 0:
                # remove empty trades
                buys_daily_slices.pop(buy_date)

        capital_gain_line: CapitalGainLine = capital_gain_line_accumulator.finalize()
        capital_gain_lines.append(capital_gain_line)

    sale_actions.clear()
    if len(sales_daily_slices) > 0:
        for trade_part in sales_daily_slices.values():
            process_remaining_trades(sale_actions, trade_part)
        logger.debug("Leftover sales_daily_slices:")
        log_day_partitioned_trades(sales_daily_slices, "Leftover sales_daily_slices")
        logger.debug(f"Leftover sale_actions: {sale_actions}")

    buy_actions.clear()
    if len(buys_daily_slices) > 0:
        for trade_part in buys_daily_slices.values():
            process_remaining_trades(buy_actions, trade_part)
        logger.debug("Leftover buys_daily_slices:")
        log_day_partitioned_trades(buys_daily_slices, "Leftover buys_daily_slices")
        logger.debug(f"Leftover buy_actions: {buy_actions}")

    logger.debug(f"Final capital_gain_lines: {len(capital_gain_lines)} lines")

    return capital_gain_lines


def process_remaining_trades(
    buy_actions: QuantitatedTradeActions, trade_part: TradePartsWithinDay
) -> None:
    total: Decimal = trade_part.quantity()
    for trade in trade_part.get_trades():
        if total == 0:
            raise DataValidationError("Total quantity is 0!")
        if trade.quantity > total:
            buy_actions.append(QuantitatedTradeAction(total, trade))
            total = Decimal(0)
        else:
            total -= trade.quantity
            buy_actions.append(QuantitatedTradeAction(trade.quantity, trade))


def extract_trades(
    quantity_left: Decimal,
    trade_parts: TradePartsWithinDay,
    capital_gain_line_accumulator: CapitalGainLineAccumulator,
) -> None:
    while quantity_left > 0:
        part = trade_parts.pop_trade_part()
        quantity_left -= part.quantity
        if quantity_left >= 0:
            capital_gain_line_accumulator.add_trade(part.quantity, part.action)
        else:
            capital_gain_line_accumulator.add_trade(part.quantity + quantity_left, part.action)
            trade_parts.push_trade_part(-quantity_left, part.action)
            quantity_left = 0


def split_by_days(actions: QuantitatedTradeActions, trade_type: TradeType) -> DayPartitionedTrades:
    """
    Split trade actions by day for FIFO matching.

    Args:
        actions: List of quantitated trade actions
        trade_type: Type of trades to process

    Returns:
        Dictionary mapping trade dates to trade parts within day
    """
    logger = get_logger(__name__)
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
        trade_date = get_trade_date(trade_action.date_time)
        trades_within_day: TradePartsWithinDay = day_partitioned_trades.get(
            trade_date, TradePartsWithinDay()
        )
        logger.debug(f"pushing trade action {trade_action}")
        trades_within_day.push_trade_part(quantity, trade_action)
        day_partitioned_trades[trade_date] = trades_within_day

    return day_partitioned_trades


def calculate(
    trade_cycle_per_company: TradeCyclePerCompany,
    leftover_trades: TradeCyclePerCompany,
    capital_gains: CapitalGainLinesPerCompany,
) -> None:
    """
    Calculate capital gains and leftover trades for all companies.

    Args:
        trade_cycle_per_company: Input trade cycles grouped by company and currency
        leftover_trades: Output container for unmatched trades
        capital_gains: Output container for calculated capital gains
    """
    company_currency: CurrencyCompany
    trade_cycle: TradeCycle
    for company_currency, trade_cycle in trade_cycle_per_company.items():
        currency = company_currency.currency
        company = company_currency.company
        trade_cycle.validate(currency, company)
        if not trade_cycle.has_sold() or not trade_cycle.has_bought():
            leftover_trades[company_currency] = trade_cycle
            continue
        capital_gain_lines: CapitalGainLines = capital_gains_for_company(
            trade_cycle, company, currency
        )
        if not trade_cycle.is_empty():
            leftover_trades[company_currency] = trade_cycle
        capital_gains[CurrencyCompany(currency, company)] = capital_gain_lines
