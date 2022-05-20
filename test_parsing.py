import unittest
from pathlib import Path

import parsing
from reporting import split_by_months
from supplementary import TradeActionsPerCompany, TradeType, TradeAction, CapitalGainLineAccumulator
from test_common_data import simple_trade, test_symbol


class MyTestCase(unittest.TestCase):

    def test_parsing(self):
        source_file = Path('resources', 'simple.csv')
        actual_trades = parsing.parse_data(source_file)
        self.assertEqual(simple_trade[test_symbol][TradeType.BUY], actual_trades[test_symbol][TradeType.BUY])
        self.assertEqual(simple_trade[test_symbol][TradeType.SELL][1], actual_trades[test_symbol][TradeType.SELL][1])
        self.assertEqual(simple_trade[test_symbol][TradeType.SELL], actual_trades[test_symbol][TradeType.SELL])
        self.assertEqual(simple_trade, actual_trades)

    @staticmethod
    def test_capital_gain_lines():
        source_file = Path('resources', 'simple.csv')
        actual_trades: TradeActionsPerCompany = parsing.parse_data(source_file)
        xlsx_file = Path('resources', 'capital_gains.xlsx')
        actual_trades: TradeActionsPerCompany = parsing.parse_results(xlsx_file)
        results_source_file = "resources/capital_gains.csv"
        #complete_trades = reporting.extract_complete_trades(actual_trades)


if __name__ == '__main__':
    unittest.main()
