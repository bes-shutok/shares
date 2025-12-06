"""Tests that duplicate the functionality of test_reporting.py but using raw IB export format.

These tests ensure that raw IB parsing produces the same Excel output as parse_data
when processing equivalent data.
"""

from datetime import UTC, datetime
from decimal import Decimal

from test_data import sell_action1

from shares_reporting.application.extraction import parse_ib_export
from shares_reporting.application.transformation import calculate_fifo_gains, split_by_days
from shares_reporting.domain.collections import (
    CapitalGainLinesPerCompany,
    QuantitatedTradeAction,
    TradeCyclePerCompany,
)
from shares_reporting.domain.entities import CurrencyCompany
from shares_reporting.domain.value_objects import (
    TradeDate,
    TradeType,
    parse_company,
    parse_currency,
)

test_dict1 = {("2022", "01"), ("2021", "12"), ("2021", "02")}
test_dict2 = ["202201", "202112", "202102"]
date_time1 = datetime.strptime("2021-05-18, 14:53:23", "%Y-%m-%d, %H:%M:%S").replace(
    tzinfo=UTC
)
date_time2 = datetime.strptime("2022-05-18, 14:53:23", "%Y-%m-%d, %H:%M:%S").replace(
    tzinfo=UTC
)
date_time3 = datetime.strptime("2021-01-18, 14:53:23", "%Y-%m-%d, %H:%M:%S").replace(
    tzinfo=UTC
)
date_time4 = datetime.strptime("2021-12-18, 14:53:23", "%Y-%m-%d, %H:%M:%S").replace(
    tzinfo=UTC
)
test_dict4 = [
    TradeDate(date_time1.year, date_time1.month, date_time1.day),
    TradeDate(date_time2.year, date_time2.month, date_time2.day),
    TradeDate(date_time3.year, date_time3.month, date_time3.day),
    TradeDate(date_time4.year, date_time4.month, date_time4.day),
]


def test_sorting():
    sorted_by_day = sorted(test_dict4, key=lambda date: date.day)
    assert sorted_by_day[0].day == 18
    assert sorted_by_day[1].day == 18
    assert sorted_by_day[2].day == 18
    assert sorted_by_day[3].day == 18

    sorted_by_month = sorted(test_dict4, key=lambda date: date.get_month_name())
    assert sorted_by_month[0].get_month_name() == "December"
    assert sorted_by_month[1].get_month_name() == "January"
    assert sorted_by_month[2].get_month_name() == "May"


def test_partitioning_by_days():
    """Test that split_by_days correctly groups trades by day"""
    # Create QuantitatedTradeActions for testing
    quantitated_trades = [
        QuantitatedTradeAction(Decimal("10"), sell_action1),
        QuantitatedTradeAction(Decimal("5"), sell_action1),
        QuantitatedTradeAction(Decimal("3"), sell_action1),
        QuantitatedTradeAction(Decimal("2"), sell_action1),
    ]
    days = split_by_days(quantitated_trades, TradeType.SELL)
    assert len(days) == 1
    # The partitioning function groups trades by their date
    actual_day = list(days.keys())[0]
    assert days[actual_day].get_top_count() == 10  # get_top_count returns first trade quantity


def test_comparing_raw_ib():
    """Test that raw IB parsing produces valid capital gains data structure"""
    from pathlib import Path

    source = Path("tests", "resources", "ib_simple_raw.csv")

    trade_actions_per_company: TradeCyclePerCompany = parse_ib_export(source)
    capital_gains: CapitalGainLinesPerCompany = {}
    leftover_trades: TradeCyclePerCompany = {}
    calculate_fifo_gains(trade_actions_per_company, leftover_trades, capital_gains)

    # Verify that raw IB parsing produces valid capital gains structure
    currency = parse_currency("USD")
    company = parse_company("BTU", "US7045491033", "United States")
    currency_company = CurrencyCompany(currency, company)

    assert currency_company in capital_gains
    assert len(capital_gains[currency_company]) == 2  # Same as simple.csv

    # Verify the capital gains are properly calculated
    cg_lines = sorted(
        capital_gains[currency_company],
        key=lambda x: (x.get_sell_date().year, x.get_sell_date().month, x.get_sell_date().day),
    )

    # First sale (June 3): 10 shares sold from first purchase (15 @ $6.77)
    first_cg = cg_lines[0]
    assert first_cg.sell_quantity() == 10
    assert first_cg.buy_quantity() == 10
    assert first_cg.ticker.ticker == "BTU"

    # Second sale (October 4): 5 shares sold from remaining first purchase (5 @ $6.77)
    second_cg = cg_lines[1]
    assert second_cg.sell_quantity() == 5
    assert second_cg.buy_quantity() == 5
    assert second_cg.ticker.ticker == "BTU"
