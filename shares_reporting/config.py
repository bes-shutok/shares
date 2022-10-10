import configparser
from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple, List


class ConversionRate(NamedTuple):
    base: str
    calculated: str
    rate: Decimal


@dataclass
class Config:
    base: str
    rates: List[ConversionRate]


# https://docs.python.org/3/library/configparser.html
def create_config():
    config = configparser.ConfigParser()
    config.optionxform = str
    config.allow_no_value = True
    config["COMMON"] = {"TARGET CURRENCY": "EUR"}
    config["EXCHANGE RATES"] = {"EUR/CAD": "0.69478",
                                "EUR/USD": "0.88292",
                                "EUR/GBP": "1.19008",
                                "EUR/HKD": "0.11321",
                                "EUR/PLN": "0.21754"}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def read_config() -> Config:
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read('../config.ini')

    target: str = config["COMMON"]["TARGET CURRENCY"]
    rates: List[ConversionRate] = []
    for key in config["EXCHANGE RATES"]:
        base, calculated = key.split("/")
        assert base == target
        rates.append(ConversionRate(base=base, calculated=calculated,  rate=Decimal(config["EXCHANGE RATES"][key])))

    return Config(base=target, rates=rates)


def main():
    create_config()


if __name__ == "__main__":
    main()
