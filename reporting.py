from pathlib import Path

from extraction import parse_data
from domain import CapitalGainLinesPerCompany, TradeActionsPerCompany
from transformation import create_extract
from persisting import persist_results


def main():
    extract = Path('resources', 'extract.xlsx')
    leftover = Path('resources', 'shares-leftover-2022.xlsx')
    source = Path('resources', 'shares.csv')
    print("Starting conversion from " + str(source) + " to " + str(extract))

    # enhance pipeline to create 'shares-leftover-YYYY.csv' with the exact same structure but leftover shares.
    # In this file only bought and left shares should be present
    trade_actions_per_company: TradeActionsPerCompany = parse_data(source)
    capital_gain_lines_per_company: CapitalGainLinesPerCompany = create_extract(trade_actions_per_company)
    persist_results(extract, leftover, capital_gain_lines_per_company)


if __name__ == "__main__":
    main()
