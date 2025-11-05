from pathlib import Path

from .application.extraction import parse_raw_ib_export
from .application.persisting import persist_leftover, persist_results
from .application.transformation import calculate
from .domain.collections import CapitalGainLinesPerCompany, TradeCyclePerCompany


def main():
    extract = Path("resources/result", "extract.xlsx")
    leftover = Path("resources/result", "shares-leftover.csv")

    # Raw IB export file
    source_file = Path("resources/source", "ib_export.csv")

    if not source_file.exists():
        raise FileNotFoundError(f"IB export file not found: {source_file}")

    print(f"Found raw IB export file: {source_file}")
    print(f"Starting conversion from {source_file} to {extract}")

    # Parse raw IB export data
    trade_lines_per_company: TradeCyclePerCompany = parse_raw_ib_export(source_file)

    leftover_trades: TradeCyclePerCompany = {}
    capital_gains: CapitalGainLinesPerCompany = {}
    calculate(trade_lines_per_company, leftover_trades, capital_gains)

    # create 'shares-leftover-YYYY.csv' with the exact same structure but leftover shares.
    # In this file only bought and left shares should be present
    persist_leftover(leftover, leftover_trades)

    persist_results(extract, capital_gains)

    print(f"Successfully processed {len(trade_lines_per_company)} trade cycles")
    print(f"Generated reports: {extract} and {leftover}")


if __name__ == "__main__":
    main()