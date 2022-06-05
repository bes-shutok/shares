import configparser


# https://docs.python.org/3/library/configparser.html
def create_config():
    config = configparser.ConfigParser()
    config.optionxform = str
    config["DEFAULT"] = {}
    config["DEFAULT"]["TARGET CURRENCY"] = "EUR"
    config["EXCHANGE RATES"] = {"EUR/CAD": "0.69478",
                                "EUR/USD": "0.88292",
                                "EUR/GBP": "1.19008",
                                "EUR/HKD": "0.11321",
                                "EUR/PLN": "0.21754"}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def main():
    create_config()


if __name__ == "__main__":
    main()
