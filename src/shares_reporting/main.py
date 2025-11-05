from pathlib import Path
from typing import Union

from .application.extraction import parse_data, parse_raw_ib_export
from .application.persisting import persist_leftover, persist_results
from .application.transformation import calculate
from .domain.collections import CapitalGainLinesPerCompany, TradeCyclePerCompany


def detect_file_type(file_path: Union[str, Path]) -> str:
    """
    Detect whether the file is a raw IB export or processed CSV.

    Args:
        file_path: Path to the CSV file

    Returns:
        'raw' if it's a raw IB export, 'processed' if it's a processed CSV
    """
    file_path = Path(file_path)

    # Check file extension and naming patterns
    if "ib_export" in file_path.name.lower():
        return "raw"

    # Try to read first few lines to detect format
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if (
                first_line.startswith("Financial Instrument Information")
                or "Trades,Header" in first_line
            ):
                return "raw"
            else:
                return "processed"
    except Exception:
        return "processed"  # Default to processed if we can't read the file


def main():
    extract = Path("resources/result", "extract.xlsx")
    leftover = Path("resources/result", "shares-leftover.csv")

    # Support both raw IB exports and processed CSV files
    raw_source = Path("resources/source", "ib_export.csv")  # Raw IB export
    processed_source = Path("resources/source", "shares.csv")  # Processed CSV (legacy)

    # Determine which file to use
    source_file = None
    file_type = None

    if raw_source.exists():
        source_file = raw_source
        file_type = "raw"
        print(f"Found raw IB export file: {source_file}")
    elif processed_source.exists():
        source_file = processed_source
        file_type = "processed"
        print(f"Found processed CSV file: {source_file}")
    else:
        raise FileNotFoundError(
            f"No source file found. Expected either {raw_source} or {processed_source}"
        )

    print(f"Starting conversion from {source_file} to {extract}")

    # Parse data based on file type
    if file_type == "raw":
        trade_lines_per_company: TradeCyclePerCompany = parse_raw_ib_export(source_file)
    else:
        trade_lines_per_company: TradeCyclePerCompany = parse_data(source_file)

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
