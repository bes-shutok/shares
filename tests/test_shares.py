import unittest
from pathlib import Path

import extraction
import data
import domain


class MyTestCase(unittest.TestCase):

    def test_parsing(self):
        source_file = Path('resources', 'simple.csv')
        actual_trades: domain.TradeActionsPerCompany = extraction.parse_data(source_file)
        self.assertEqual(
            data.simple_trade[data.currency_company][domain.TradeType.BUY],
            actual_trades[data.currency_company][domain.TradeType.BUY]
        )
        self.assertEqual(
            data.simple_trade[data.currency_company][domain.TradeType.SELL][1],
            actual_trades[data.currency_company][domain.TradeType.SELL][1]
        )
        self.assertEqual(
            data.simple_trade[data.currency_company][domain.TradeType.SELL],
            actual_trades[data.currency_company][domain.TradeType.SELL]
        )
        self.assertEqual(data.simple_trade, actual_trades)


if __name__ == '__main__':
    unittest.main()
