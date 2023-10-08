from pathlib import Path

import extraction as extraction
import test_data as test_data
import domain as domain


def test_parsing():
    source_file = Path('tests', 'resources', 'simple.csv')
    actual_trades: domain.TradeCyclePerCompany = extraction.parse_data(source_file)
    assert test_data.simple_trade[test_data.currency_company].get(domain.TradeType.BUY) == actual_trades[test_data.currency_company].get(domain.TradeType.BUY)
    assert test_data.simple_trade[test_data.currency_company].get(domain.TradeType.SELL)[1] == actual_trades[test_data.currency_company].get(domain.TradeType.SELL)[1]
    assert test_data.simple_trade[test_data.currency_company].get(domain.TradeType.SELL) == actual_trades[test_data.currency_company].get(domain.TradeType.SELL)
    assert test_data.simple_trade == actual_trades
    