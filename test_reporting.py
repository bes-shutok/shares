import unittest


class MyTestCase(unittest.TestCase):

    def test_parsing(self):
        source_file = Path('resources', 'simple.csv')
        actual_trades = parsing.parse_data(source_file)
        self.assertEqual(simple_trade[symbol][TradeType.BUY], actual_trades[symbol][TradeType.BUY])
        self.assertEqual(simple_trade[symbol][TradeType.SELL][1], actual_trades[symbol][TradeType.SELL][1])
        self.assertEqual(simple_trade[symbol][TradeType.SELL], actual_trades[symbol][TradeType.SELL])
        self.assertEqual(simple_trade, actual_trades)

    def test_capital_gain_lines(self):
        source_file = Path('resources', 'simple.csv')
        actual_trades: TradeActionsPerCompany = parsing.parse_data(source_file)
        xlsx_file = Path('resources', 'capital_gains.xlsx')
        actual_trades: TradeActionsPerCompany = parsing.parse_results(xlsx_file)
        #results_source_file = "resources/capital_gains.csv"
        #complete_trades = reporting.extract_complete_trades(actual_trades)


if __name__ == '__main__':
    unittest.main()
