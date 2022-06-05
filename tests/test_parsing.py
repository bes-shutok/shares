import unittest
from pathlib import Path

from domain import TradeType, TradeActionsPerCompany
from extraction import parse_data
from data import simple_trade, currency_symbol


class MyTestCase(unittest.TestCase):

    def test_parsing(self):
        source_file = Path('./resources', 'simple.csv')
        actual_trades: TradeActionsPerCompany = parse_data(source_file)
        self.assertEqual(simple_trade[currency_symbol][TradeType.BUY], actual_trades[currency_symbol][TradeType.BUY])
        self.assertEqual(simple_trade[currency_symbol][TradeType.SELL][1], actual_trades[currency_symbol][TradeType.SELL][1])
        self.assertEqual(simple_trade[currency_symbol][TradeType.SELL], actual_trades[currency_symbol][TradeType.SELL])
        self.assertEqual(simple_trade, actual_trades)


if __name__ == '__main__':
    unittest.main()
