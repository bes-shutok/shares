"""
Main entry point for the shares reporting application.

Processes Interactive Brokers CSV exports to generate tax reporting data for capital gains calculations.
"""

import sys
from pathlib import Path

from .application.extraction import parse_ib_export_all
from .application.persisting import export_rollover_file, generate_tax_report
from .application.transformation import calculate_fifo_gains
from .domain.collections import (
    CapitalGainLinesPerCompany,
    DividendIncomePerCompany,
    IBExportData,
    TradeCyclePerCompany,
)
from .domain.exceptions import FileProcessingError, ReportGenerationError, SharesReportingError
from .infrastructure.logging_config import configure_application_logging, create_module_logger
from .infrastructure.validation import validate_output_directory


def main(
    source_file: Path | None = None, output_dir: Path | None = None, log_level: str = "INFO"
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
    configure_application_logging(level=log_level, log_file=log_file)
    logger = create_module_logger(__name__)

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

        # Extract comprehensive data from IB export
        try:
            ib_data: IBExportData = parse_ib_export_all(validated_source)
            trade_lines_per_company: TradeCyclePerCompany = ib_data.trade_cycles
            dividend_income_per_company: DividendIncomePerCompany = ib_data.dividend_income
            logger.info(
                f"Parsed {len(trade_lines_per_company)} trade cycles and {len(dividend_income_per_company)} dividend entries"
            )
        except Exception as e:
            raise FileProcessingError(f"Failed to parse source file: {e}") from e

        # Calculate capital gains using FIFO matching algorithm
        try:
            leftover_trades: TradeCyclePerCompany = {}
            capital_gains: CapitalGainLinesPerCompany = {}
            calculate_fifo_gains(trade_lines_per_company, leftover_trades, capital_gains)
            logger.info(
                f"Calculated {sum(len(gains) for gains in capital_gains.values())} capital gain lines"
            )
        except Exception as e:
            raise SharesReportingError(f"Failed to calculate capital gains: {e}") from e

        # Export unmatched securities rollover file
        try:
            export_rollover_file(leftover_path, leftover_trades)
            logger.info(f"Generated unmatched securities rollover file: {leftover_path}")
        except Exception as e:
            raise ReportGenerationError(
                f"Failed to generate unmatched securities rollover file: {e}"
            ) from e

        # Generate comprehensive tax report
        try:
            generate_tax_report(extract_path, capital_gains, dividend_income_per_company)
            report_type = (
                "capital gains and dividend income"
                if dividend_income_per_company
                else "capital gains"
            )
            logger.info(f"Generated {report_type} report: {extract_path}")
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate report: {e}") from e

        logger.info("Application completed successfully")
        logger.info(f"Output directory: {validated_output_dir.name}")
        report_type = (
            "capital gains and dividend income" if dividend_income_per_company else "capital gains"
        )
        logger.info(f"Generated {report_type} report: {extract_path.name}")
        logger.info(f"Leftover shares report: {leftover_path.name}")
        logger.info(
            f"Processed {len(trade_lines_per_company)} trade cycles and {len(dividend_income_per_company)} dividend entries"
        )
        print("Processing completed successfully!")

    except SharesReportingError as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Unexpected error: {e}")
        print("Check logs for detailed information")
        sys.exit(1)


if __name__ == "__main__":
    main()
