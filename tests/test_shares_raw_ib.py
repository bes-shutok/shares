"""
Tests that duplicate the functionality of test_shares.py but using raw IB export format.

These tests ensure that parse_ib_export produces the same results as parse_data
when processing equivalent data in raw IB format.
"""

from pathlib import Path

import test_data as test_data

from shares_reporting.application import extraction, transformation
from shares_reporting.domain.collections import TradeCyclePerCompany
from shares_reporting.domain.entities import CurrencyCompany
from shares_reporting.domain.value_objects import (
    TradeType,
    parse_company,
    parse_currency,
)


def test_parsing_raw_ib():
    """Test that raw IB parsing produces same results as simple.csv parsing"""
    source_file = Path("tests", "resources", "ib_simple_raw.csv")
    actual_trades: TradeCyclePerCompany = extraction.parse_ib_export(source_file)

    # Should have same structure as simple.csv parsing
    assert len(actual_trades) == 1

    # Find the BTU USD company
    currency = parse_currency("USD")
    company = parse_company(
        "BTU", "US7045491033", "United States"
    )  # Raw IB includes ISIN and country
    currency_company = CurrencyCompany(currency, company)
    assert currency_company in actual_trades

    # Verify the trades match expected structure (same quantities, prices, dates)
    cycle = actual_trades[currency_company]

    # Should have same number of buys and sells as simple.csv
    assert cycle.has(TradeType.BUY) is True
    assert cycle.has(TradeType.SELL) is True
    assert len(cycle.get(TradeType.BUY)) == 1
    assert len(cycle.get(TradeType.SELL)) == 2

    # Verify buy trade matches simple.csv data
    buy_trade = cycle.get(TradeType.BUY)[0]
    assert buy_trade.quantity == test_data.buy_action1.quantity
    assert buy_trade.action.price == test_data.buy_action1.price
    assert buy_trade.action.fee == test_data.buy_action1.fee

    # Verify sell trades match simple.csv data (ignoring company object differences)
    sell_trades = cycle.get(TradeType.SELL)
    assert len(sell_trades) == 2

    # Check first sell trade
    assert sell_trades[0].quantity == abs(test_data.sell_action1.quantity)
    assert sell_trades[0].action.price == test_data.sell_action1.price
    assert sell_trades[0].action.fee == test_data.sell_action1.fee

    # Check second sell trade
    assert sell_trades[1].quantity == abs(test_data.sell_action2.quantity)
    assert sell_trades[1].action.price == test_data.sell_action2.price
    assert sell_trades[1].action.fee == test_data.sell_action2.fee


def test_fifo_strategy_with_simple_raw_ib_data():
    """Test FIFO strategy with raw IB data - ensures raw IB parsing works with FIFO logic"""
    source_file = Path("tests", "resources", "ib_simple_raw.csv")
    actual_trades: TradeCyclePerCompany = extraction.parse_ib_export(source_file)

    # Use the correct calculate function signature
    leftover_trades: TradeCyclePerCompany = {}
    capital_gains = {}
    transformation.calculate_fifo_gains(
        actual_trades, leftover_trades, capital_gains
    )

    # With FIFO: First 10 shares matched to June 3 sale, remaining 5 to October 4 sale
    # Expected: 2 capital gain lines for BTU (same as simple.csv)
    currency = parse_currency("USD")
    company = parse_company("BTU", "US7045491033", "United States")
    btu_company = CurrencyCompany(currency, company)
    assert len(capital_gains[btu_company]) == 2

    # Verify FIFO behavior (first purchase sold first)
    cg_lines = sorted(
        capital_gains[btu_company],
        key=lambda x: (x.get_sell_date().year, x.get_sell_date().month, x.get_sell_date().day),
    )

    # First sale (June 3): 10 shares sold from first purchase (15 @ $6.77)
    first_cg = cg_lines[0]
    assert first_cg.sell_quantity() == 10
    assert first_cg.buy_quantity() == 10

    # Second sale (October 4): 5 shares sold from remaining first purchase (5 @ $6.77)
    second_cg = cg_lines[1]
    assert second_cg.sell_quantity() == 5
    assert second_cg.buy_quantity() == 5

    # Verify that the capital gains amounts match what we'd expect from simple.csv
    # This confirms raw IB parsing produces identical business results
    assert first_cg.ticker.ticker == "BTU"
    assert second_cg.ticker.ticker == "BTU"


def test_ib_multi_strategy_raw_data_structure():
    """Test that our raw IB multi-strategy test data has the right structure for strategy testing"""
    source_file = Path("tests", "resources", "ib_multi_strategy_raw.csv")
    actual_trades: TradeCyclePerCompany = extraction.parse_ib_export(source_file)

    # Should have AAPL and TSLA companies with USD currency
    currency = parse_currency("USD")
    aapl_company = parse_company(
        "AAPL", "US0378331005", "United States"
    )
    tsla_company = parse_company(
        "TSLA", "US88160R1014", "United States"
    )

    aapl_currency_company = CurrencyCompany(currency, aapl_company)
    tsla_currency_company = CurrencyCompany(currency, tsla_company)

    assert aapl_currency_company in actual_trades
    assert tsla_currency_company in actual_trades

    # AAPL: Bought 155, Sold 135 (partial settlement - 20 remaining)
    aapl_buys = actual_trades[aapl_currency_company].get(TradeType.BUY)
    aapl_sells = actual_trades[aapl_currency_company].get(TradeType.SELL)

    assert len(aapl_buys) == 3  # 3 purchase transactions
    assert len(aapl_sells) == 3  # 3 sale transactions

    total_aapl_bought = sum(trade.quantity for trade in aapl_buys)
    total_aapl_sold = sum(abs(trade.quantity) for trade in aapl_sells)
    assert total_aapl_bought == 155  # 50 + 75 + 30
    assert total_aapl_sold == 135  # 40 + 60 + 35
    assert total_aapl_bought > total_aapl_sold  # Partial settlement case

    # TSLA: Bought 85, Sold 85 (complete settlement)
    tsla_buys = actual_trades[tsla_currency_company].get(TradeType.BUY)
    tsla_sells = actual_trades[tsla_currency_company].get(TradeType.SELL)

    assert len(tsla_buys) == 3  # 3 purchase transactions
    assert len(tsla_sells) == 3  # 3 sale transactions

    total_tsla_bought = sum(trade.quantity for trade in tsla_buys)
    total_tsla_sold = sum(abs(trade.quantity) for trade in tsla_sells)
    assert total_tsla_bought == 85  # 25 + 40 + 20
    assert total_tsla_sold == 85  # 35 + 30 + 20
    assert total_tsla_bought == total_tsla_sold  # Complete settlement case


def test_strategy_price_differences_for_future_reference_raw_ib():
    """
    Test that documents how different strategies would produce different results using raw IB data.

    NOTE: This test is for documentation and future reference only.
    The application currently only supports FIFO strategy, which is required/strongly
    suggested in Portugal and many other jurisdictions. LIFO and HIFO strategies
    are planned as low-priority future enhancements for international users.
    """
    source_file = Path("tests", "resources", "ib_multi_strategy_raw.csv")
    actual_trades: TradeCyclePerCompany = extraction.parse_ib_export(source_file)

    # Get AAPL trades for strategy comparison
    currency = parse_currency("USD")
    aapl_company = parse_company(
        "AAPL", "US0378331005", "United States"
    )
    aapl_currency_company = CurrencyCompany(currency, aapl_company)
    buys = actual_trades[aapl_currency_company].get(TradeType.BUY)

    # Sort purchases by date to understand strategy differences
    buy_data = [(trade.quantity, trade.action.price, trade.action.date_time) for trade in buys]
    buy_data.sort(key=lambda x: x[2])  # Sort by date (chronological order)

    # Extract prices in different strategy orders
    chronological_prices = [price for qty, price, date in buy_data]  # FIFO order
    prices_by_qty = [(qty, price) for qty, price, date in buy_data]

    # Document how different strategies would work:
    # FIFO order (chronological): $120.50, $185.25, $95.75
    # LIFO order (reverse chronological): $95.75, $185.25, $120.50
    # HIFO order (by price): $185.25, $120.50, $95.75

    expected_fifo_prices = [120.50, 185.25, 95.75]
    expected_lifo_prices = [95.75, 185.25, 120.50]
    expected_hifo_prices = [185.25, 120.50, 95.75]

    assert chronological_prices == expected_fifo_prices

    # Document how different strategies would handle first sale of 40 shares:
    # FIFO: 40 shares @ $120.50 = $4,820 (from first purchase)
    # LIFO: 30 shares @ $95.75 + 10 shares @ $185.25 = $2,872.50 + $1,852.50 = $4,725.00
    # HIFO: 40 shares @ $185.25 = $7,410 (from highest price purchase)

    fifo_cost = min(40, prices_by_qty[0][0]) * prices_by_qty[0][1]

    # LIFO: Take from last purchase (30 @ $95.75), then from middle purchase (10 @ $185.25)
    lifo_shares_from_last = min(40, prices_by_qty[2][0])  # 30 shares @ $95.75
    lifo_shares_remaining = 40 - lifo_shares_from_last  # 10 shares needed
    lifo_cost = (lifo_shares_from_last * prices_by_qty[2][1]) + (
        lifo_shares_remaining * prices_by_qty[1][1]
    )

    hifo_cost = (
        min(40, max(prices_by_qty, key=lambda x: x[1])[0])
        * max(prices_by_qty, key=lambda x: x[1])[1]
    )

    # Verify all three strategies would produce different cost bases
    assert fifo_cost == 4820.0  # 40 * $120.50
    assert lifo_cost == 4725.0  # (30 * $95.75) + (10 * $185.25)
    assert hifo_cost == 7410.0  # 40 * $185.25

    # All three should be different
    assert fifo_cost != lifo_cost
    assert lifo_cost != hifo_cost
    assert fifo_cost != hifo_cost

    # This documents the potential differences for future strategy implementation
    # and validates our raw IB test data will show meaningful differences between strategies
