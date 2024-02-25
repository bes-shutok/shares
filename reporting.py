from pathlib import Path

from extraction import parse_data
from domain import CapitalGainLinesPerCompany, TradeCyclePerCompany
from transformation import calculate
from persisting import persist_results, persist_leftover


def main():
    extract = Path('resources/result', 'extract.xlsx')
    leftover = Path('resources/result', 'shares-leftover.csv')
    source = Path('resources/source', 'shares.csv')
    print("Starting conversion from " + str(source) + " to " + str(extract))

    trade_lines_per_company: TradeCyclePerCompany = parse_data(source)

    leftover_trades: TradeCyclePerCompany = {}
    capital_gains: CapitalGainLinesPerCompany = {}
    calculate(trade_lines_per_company, leftover_trades, capital_gains)

    # create 'shares-leftover-YYYY.csv' with the exact same structure but leftover shares.
    # In this file only bought and left shares should be present
    persist_leftover(leftover, leftover_trades)

    persist_results(extract, capital_gains)


if __name__ == "__main__":
    main()
