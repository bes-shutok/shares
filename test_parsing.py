import unittest
import reporting
from trade_classes import TradeActionsPerCompany, TradeType, TradeAction

currency = "USD"
company = "BTU"
buy_date = "2021-05-18, 14:53:23"
sell_date1 = "2021-06-03, 11:44:04"
sell_date2 = "2021-10-04, 09:44:11"
buy_quantity = "15"
sell_quantity1 = "-10"
sell_quantity2 = "-5"
buy_price = "6.77"
sell_price1 = "7.875"
sell_price2 = "17.36"
buy_fee = "-0.36225725"
sell_fee1 = "-0.353848875"
sell_fee2 = "-0.35229493"
simple_trade: TradeActionsPerCompany = {company: {
    TradeType.BUY: [
        (int(buy_quantity), TradeAction(company, buy_date, currency, buy_quantity, buy_price, buy_fee))
    ],
    TradeType.SELL: [
        (abs(int(sell_quantity1)), TradeAction(company, sell_date1, currency, sell_quantity1, sell_price1, sell_fee1)),
        (abs(int(sell_quantity2)), TradeAction(company, sell_date2, currency, sell_quantity2, sell_price2, sell_fee2))
    ]
}}


class MyTestCase(unittest.TestCase):

    def test_parsing(self):
        source_file = "resources/simple.csv"
        actual_trade = reporting.parse_data(source_file)
        # self.assertEqual(simple_trade[company][TradeType.BUY], actual_trade[company][TradeType.BUY])  # add assertion here
        # self.assertEqual(simple_trade[company][TradeType.SELL][1], actual_trade[company][TradeType.SELL][1])  # add assertion here
        # self.assertEqual(simple_trade[company][TradeType.SELL], actual_trade[company][TradeType.SELL])  # add assertion here
        self.assertEqual(simple_trade, actual_trade)  # add assertion here


if __name__ == '__main__':
    unittest.main()
