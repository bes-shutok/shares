"""
Main entry point for the shares reporting application.

Processes Interactive Brokers CSV exports to generate tax reporting data for capital gains calculations.
"""

import sys
from pathlib import Path
from typing import Optional

from .application.extraction import parse_raw_ib_export
from .application.persisting import persist_leftover, persist_results
from .application.transformation import calculate
from .domain.collections import CapitalGainLinesPerCompany, TradeCyclePerCompany
from .domain.exceptions import SharesReportingError, FileProcessingError, ReportGenerationError
from .infrastructure.logging_config import setup_logging, get_logger
from .infrastructure.validation import validate_output_directory


def main(
    source_file: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    log_level: str = "INFO"
) -> None:
    """
    Main application entry point.

    Args:
        source_file: Path to the source IB export CSV file
        output_dir: Directory for output files
        log_level: Logging level
    """
    # Set up logging
    log_file = Path("logs", "shares-reporting.log") if output_dir else None
    setup_logging(level=log_level, log_file=log_file)
    logger = get_logger(__name__)

    try:
        # Default paths
        if source_file is None:
            source_file = Path("resources/source", "ib_export.csv")

        if output_dir is None:
            output_dir = Path("resources/result")

        extract_path = output_dir / "extract.xlsx"
        leftover_path = output_dir / "shares-leftover.csv"

        logger.info("Starting shares reporting application")
        logger.info(f"Source file: {source_file}")
        logger.info(f"Output directory: {output_dir}")

        # Validate input file path
        try:
            validated_source = Path(source_file)
            if not validated_source.exists():
                raise FileNotFoundError(f"Source file not found: {validated_source}")
            if not validated_source.is_file():
                raise FileProcessingError(f"Source path is not a file: {validated_source}")
        except Exception as e:
            raise FileProcessingError(f"Invalid source file: {e}") from e

        # Validate output directory
        try:
            validated_output_dir = validate_output_directory(output_dir)
        except Exception as e:
            raise ReportGenerationError(f"Invalid output directory: {e}") from e

        # Update paths with validated paths
        extract_path = validated_output_dir / "extract.xlsx"
        leftover_path = validated_output_dir / "shares-leftover.csv"

        logger.info(f"Processing file: {validated_source.name}")
        logger.info(f"Output files will be: {extract_path.name} and {leftover_path.name}")

        # Parse raw IB export data
        try:
            trade_lines_per_company: TradeCyclePerCompany = parse_raw_ib_export(validated_source)
            logger.info(f"Parsed {len(trade_lines_per_company)} trade cycles")
        except Exception as e:
            raise FileProcessingError(f"Failed to parse source file: {e}") from e

        # Calculate capital gains
        try:
            leftover_trades: TradeCyclePerCompany = {}
            capital_gains: CapitalGainLinesPerCompany = {}
            calculate(trade_lines_per_company, leftover_trades, capital_gains)
            logger.info(f"Calculated {sum(len(gains) for gains in capital_gains.values())} capital gain lines")
        except Exception as e:
            raise SharesReportingError(f"Failed to calculate capital gains: {e}") from e

        # Generate leftover shares report
        try:
            persist_leftover(leftover_path, leftover_trades)
            logger.info(f"Generated leftover shares report: {leftover_path}")
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate leftover report: {e}") from e

        # Generate capital gains report
        try:
            persist_results(extract_path, capital_gains)
            logger.info(f"Generated capital gains report: {extract_path}")
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate capital gains report: {e}") from e

        logger.info("Application completed successfully")
        logger.info(f"Output directory: {validated_output_dir.name}")
        logger.info(f"Capital gains report: {extract_path.name}")
        logger.info(f"Leftover shares report: {leftover_path.name}")
        logger.info(f"Processed {len(trade_lines_per_company)} trade cycles")
        print("✅ Processing completed successfully!")

    except SharesReportingError as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}")
        print("Check logs for detailed information")
        sys.exit(1)


if __name__ == "__main__":
    main()
