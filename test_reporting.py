import unittest
import calendar
from datetime import datetime

from supplementary import get_ym_pair, get_year_month, YearMonth


class MyTestCase(unittest.TestCase):
    test_dict1 = {("2022", "01"), ("2021", "12"), ("2021", "02")}
    test_dict2 = ["202201", "202112", "202102"]
    date_time1 = datetime.strptime("2021-05-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
    date_time2 = datetime.strptime("2022-05-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
    date_time3 = datetime.strptime("2021-01-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
    date_time4 = datetime.strptime("2021-12-18, 14:53:23", '%Y-%m-%d, %H:%M:%S')
    test_dict3 = [get_ym_pair(date_time1), get_ym_pair(date_time2), get_ym_pair(date_time3), get_ym_pair(date_time4)]
    test_dict4 = [get_year_month(date_time1), get_year_month(date_time2), get_year_month(date_time3),
                  get_year_month(date_time4)]
    test_dict5 = [YearMonth(date_time1), YearMonth(date_time2), YearMonth(date_time3), YearMonth(date_time4)]

    def test_sorting(self):
        print(str(self.test_dict1))
        print(str(sorted(self.test_dict1)))
        print(str(self.test_dict2))
        print(str(sorted(self.test_dict2)))
        print(str(self.test_dict3))
        print(str(sorted(self.test_dict3)))
        # print(str(self.test_dict4))
        # print(str(sorted(self.test_dict4)))
        # for m in self.test_dict4:
        #    print(m[1])
        #    print(calendar.month_name[m[1]])
        #    print(calendar.month_abbr[m[1]])

        print(self.test_dict5)
        print(str(sorted(self.test_dict5)))


if __name__ == '__main__':
    unittest.main()
