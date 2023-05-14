import unittest
from typing import List

import requests
from bs4 import BeautifulSoup


def get_html(url: str) -> List[str]:
    r = requests.get(url).text
    soup = BeautifulSoup(r, 'html.parser')
    return soup.find('div', class_='form-item form-type-textfield form-item-result-value').text.split()


class MyTestCase(unittest.TestCase):

    def test_exchange_parsing(self):
        # date 31/12/2021
        url = "https://www.bportugal.pt/en/conversor-moeda?from=EUR&to=USD&date=1640908800&value=1.00"
        expected = ['1', 'EUR', '=', '1.13260', 'USD']
        result = get_html(url)
        print(result)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
