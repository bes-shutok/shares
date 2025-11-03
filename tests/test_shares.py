from pathlib import Path

from shares_reporting.application import extraction, transformation
from shares_reporting.domain.collections import TradeCyclePerCompany
from shares_reporting.domain.value_objects import TradeType, get_company, get_currency
from shares_reporting.domain.entities import CurrencyCompany
import test_data as test_data


def test_parsing():
    source_file = Path('tests', 'resources', 'simple.csv')
    actual_trades: TradeCyclePerCompany = extraction.parse_data(source_file)
    assert test_data.simple_trade[test_data.currency_company].get(TradeType.BUY) == actual_trades[test_data.currency_company].get(TradeType.BUY)
    assert test_data.simple_trade[test_data.currency_company].get(TradeType.SELL)[1] == actual_trades[test_data.currency_company].get(TradeType.SELL)[1]
    assert test_data.simple_trade[test_data.currency_company].get(TradeType.SELL) == actual_trades[test_data.currency_company].get(TradeType.SELL)
    assert test_data.simple_trade == actual_trades


def test_fifo_strategy_with_simple_data():
    """Test FIFO strategy with simple.csv data - ensures current functionality still works"""
    source_file = Path('tests', 'resources', 'simple.csv')
    actual_trades: TradeCyclePerCompany = extraction.parse_data(source_file)

    # Use the correct calculate function signature
    leftover_trades: TradeCyclePerCompany = {}
    capital_gains = {}
    transformation.calculate(actual_trades, leftover_trades, capital_gains)

    # With FIFO: First 10 shares matched to June 3 sale, remaining 5 to October 4 sale
    # Expected: 2 capital gain lines for BTU
    btu_company = CurrencyCompany(get_currency("USD"), get_company("BTU"))
    assert len(capital_gains[btu_company]) == 2

    # Verify FIFO behavior (first purchase sold first)
    cg_lines = sorted(capital_gains[btu_company], key=lambda x: (x.get_sell_date().year, x.get_sell_date().month, x.get_sell_date().day))

    # First sale (June 3): 10 shares sold from first purchase (15 @ $6.77)
    first_cg = cg_lines[0]
    assert first_cg.sell_quantity() == 10
    assert first_cg.buy_quantity() == 10

    # Second sale (October 4): 5 shares sold from remaining first purchase (5 @ $6.77)
    second_cg = cg_lines[1]
    assert second_cg.sell_quantity() == 5
    assert second_cg.buy_quantity() == 5


def test_ib_multi_strategy_data_structure():
    """Test that our IB multi-strategy test data has the right structure for strategy testing"""
    source_file = Path('tests', 'resources', 'ib_multi_strategy_test.csv')
    actual_trades: TradeCyclePerCompany = extraction.parse_data(source_file)

    # Should have AAPL and TSLA companies with USD currency
    aapl_company = CurrencyCompany(get_currency("USD"), get_company("AAPL"))
    tsla_company = CurrencyCompany(get_currency("USD"), get_company("TSLA"))

    assert aapl_company in actual_trades
    assert tsla_company in actual_trades

    # AAPL: Bought 155, Sold 135 (partial settlement - 20 remaining)
    aapl_buys = actual_trades[aapl_company].get(TradeType.BUY)
    aapl_sells = actual_trades[aapl_company].get(TradeType.SELL)

    assert len(aapl_buys) == 3  # 3 purchase transactions
    assert len(aapl_sells) == 3  # 3 sale transactions

    total_aapl_bought = sum(trade.quantity for trade in aapl_buys)
    total_aapl_sold = sum(abs(trade.quantity) for trade in aapl_sells)
    assert total_aapl_bought == 155  # 50 + 75 + 30
    assert total_aapl_sold == 135   # 40 + 60 + 35
    assert total_aapl_bought > total_aapl_sold  # Partial settlement case

    # TSLA: Bought 85, Sold 85 (complete settlement)
    tsla_buys = actual_trades[tsla_company].get(TradeType.BUY)
    tsla_sells = actual_trades[tsla_company].get(TradeType.SELL)

    assert len(tsla_buys) == 3  # 3 purchase transactions
    assert len(tsla_sells) == 3  # 3 sale transactions

    total_tsla_bought = sum(trade.quantity for trade in tsla_buys)
    total_tsla_sold = sum(abs(trade.quantity) for trade in tsla_sells)
    assert total_tsla_bought == 85   # 25 + 40 + 20
    assert total_tsla_sold == 85    # 35 + 30 + 20
    assert total_tsla_bought == total_tsla_sold  # Complete settlement case


def test_strategy_price_differences_for_future_reference():
    """
    Test that documents how different strategies would produce different results.

    NOTE: This test is for documentation and future reference only.
    The application currently only supports FIFO strategy, which is required/strongly
    suggested in Portugal and many other jurisdictions. LIFO and HIFO strategies
    are planned as low-priority future enhancements for international users.
    """
    source_file = Path('tests', 'resources', 'ib_multi_strategy_test.csv')
    actual_trades: TradeCyclePerCompany = extraction.parse_data(source_file)

    # Get AAPL trades for strategy comparison
    aapl_company = CurrencyCompany(get_currency("USD"), get_company("AAPL"))
    buys = actual_trades[aapl_company].get(TradeType.BUY)

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
    lifo_cost = (lifo_shares_from_last * prices_by_qty[2][1]) + (lifo_shares_remaining * prices_by_qty[1][1])

    hifo_cost = min(40, max(prices_by_qty, key=lambda x: x[1])[0]) * max(prices_by_qty, key=lambda x: x[1])[1]

    # Verify all three strategies would produce different cost bases
    assert fifo_cost == 4820.0  # 40 * $120.50
    assert lifo_cost == 4725.0  # (30 * $95.75) + (10 * $185.25)
    assert hifo_cost == 7410.0  # 40 * $185.25

    # All three should be different
    assert fifo_cost != lifo_cost
    assert lifo_cost != hifo_cost
    assert fifo_cost != hifo_cost

    # This documents the potential differences for future strategy implementation
    # and validates our test data will show meaningful differences between strategies