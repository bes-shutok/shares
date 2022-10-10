from pathlib import Path

from extraction import parse_data
from domain import CapitalGainLinesPerCompany, TradeActionsPerCompany
from transformation import create_extract
from persisting import persist_results


def main():
    destination = Path('resources', 'extract.xlsx')
    source = Path('resources', 'shares.csv')
    print("Starting conversion from " + str(source) + " to " + str(destination))

    trade_actions_per_company: TradeActionsPerCompany = parse_data(source)
    capital_gain_lines_per_company: CapitalGainLinesPerCompany = create_extract(trade_actions_per_company)
    persist_results(destination, capital_gain_lines_per_company)


if __name__ == "__main__":
    main()
