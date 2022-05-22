import unittest
from datetime import datetime

from reporting import split_by_months
from supplementary import get_year_month, YearMonth, TradeType, TradePartsWithinMonth, MonthPartitionedTrades
from test_common_data import sell_action1

test_dict1 = {("2022", "01"), ("2021", "12"), ("2021", "02")}
test_dict2 = ["202201", "202112", "202102"]
date_time1 = datetime.strptime("2021-05-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
date_time2 = datetime.strptime("2022-05-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
date_time3 = datetime.strptime("2021-01-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
date_time4 = datetime.strptime("2021-12-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
test_dict4 = [get_year_month(date_time1), get_year_month(date_time2), get_year_month(date_time3),
              get_year_month(date_time4)]
test_dict5 = [YearMonth(date_time1), YearMonth(date_time2), YearMonth(date_time3), YearMonth(date_time4)]


class MyTestCase(unittest.TestCase):

    def test_sorting(self):
        print(str(test_dict1))
        print(str(sorted(test_dict1)))
        print(str(test_dict2))
        print(str(sorted(test_dict2)))
        print(str(test_dict4))
        print(str(sorted(test_dict4)))
        print(test_dict5)
        print(str(sorted(test_dict5)))
        self.assertEqual(1, 1)

    def test_partitioning(self):
        trades_within_month1 = TradePartsWithinMonth()
        trades_within_month1.push_trade_part(1, sell_action1)
        month_partitioned_trades1: MonthPartitionedTrades = {
            get_year_month(sell_action1.date_time): trades_within_month1}

        actual: MonthPartitionedTrades = split_by_months([(1, sell_action1)], TradeType.SELL)
        print(actual)
        self.assertEqual(actual, month_partitioned_trades1)


if __name__ == '__main__':
    unittest.main()
