from typing import List

import requests
from bs4 import BeautifulSoup

# API keeps changing and the exchange course is needed only once per year - easier to do manually

# def get_html(url: str) -> List[str]:
#     r = requests.get(url).text
#     soup = BeautifulSoup(r, 'html.parser')
#     return soup.find('div', class_='form-item form-type-textfield form-item-result-value').text.split()


#
# def test_exchange_parsing():
#     # date 31/12/2021
#     url = "https://www.bportugal.pt/en/conversor-moeda?from=EUR&to=USD&date=1640908800&value=1.00"
#     expected = ['1', 'EUR', '=', '1.13260', 'USD']
#     result = get_html(url)
#     print(result)
#     assert result == expected