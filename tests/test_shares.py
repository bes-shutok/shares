from pathlib import Path

from shares_reporting.application import extraction
from shares_reporting.domain.collections import TradeCyclePerCompany
from shares_reporting.domain.value_objects import TradeType
import test_data as test_data


def test_parsing():
    source_file = Path('tests', 'resources', 'simple.csv')
    actual_trades: TradeCyclePerCompany = extraction.parse_data(source_file)
    assert test_data.simple_trade[test_data.currency_company].get(TradeType.BUY) == actual_trades[test_data.currency_company].get(TradeType.BUY)
    assert test_data.simple_trade[test_data.currency_company].get(TradeType.SELL)[1] == actual_trades[test_data.currency_company].get(TradeType.SELL)[1]
    assert test_data.simple_trade[test_data.currency_company].get(TradeType.SELL) == actual_trades[test_data.currency_company].get(TradeType.SELL)
    assert test_data.simple_trade == actual_trades
    