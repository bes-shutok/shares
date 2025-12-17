"""State machine orchestration for Interactive Brokers CSV parsing."""

from typing import TYPE_CHECKING

from ...domain.constants import CSV_DATA_MARKER, CSV_HEADER_MARKER, DATA_DISCRIMINATOR_COLUMN_INDEX
from ...domain.exceptions import FileProcessingError
from ...infrastructure.logging_config import create_module_logger

if TYPE_CHECKING:
    from logging import Logger
from .contexts import (
    DividendsContext,
    FinancialInstrumentContext,
    TradesContext,
    WithholdingTaxContext,
)
from .models import IBCsvData, IBCsvSection


class IBCsvStateMachine:
    """State machine for processing IB CSV files."""

    MAX_SAMPLE_SIZE: int = 2
    MIN_ROW_LENGTH: int = DATA_DISCRIMINATOR_COLUMN_INDEX
    logger: Logger
    current_section: IBCsvSection
    require_trades_section: bool
    current_row_number: int

    def __init__(self, require_trades_section: bool = True):
        """Initialize the CSV state machine.

        Args:
            require_trades_section: Whether to enforce presence of Trades section.
        """
        self.logger = create_module_logger(__name__)
        self.current_section = IBCsvSection.UNKNOWN
        self.require_trades_section = require_trades_section
        self.current_row_number = 0

        # Initialize data containers
        self.security_info: dict[str, dict[str, str]] = {}
        self.raw_trade_data: list[dict[str, str]] = []
        self.raw_dividend_data: list[dict[str, str]] = []
        self.raw_withholding_tax_data: list[dict[str, str]] = []

        # Initialize contexts
        self.financial_context: FinancialInstrumentContext = FinancialInstrumentContext(self.security_info)
        self.trades_context: TradesContext = TradesContext(self.raw_trade_data, require_trades_section)
        self.dividends_context: DividendsContext = DividendsContext(self.raw_dividend_data)
        self.withholding_tax_context: WithholdingTaxContext = WithholdingTaxContext(self.raw_withholding_tax_data)

        # Tracking
        self.found_financial_instrument_header: bool = False

    def process_row(self, row: list[str]) -> None:
        """Process a single CSV row using the state machine."""
        self.current_row_number += 1
        if len(row) < self.MIN_ROW_LENGTH:
            return

        # Check for section transitions
        if self._detect_section_transition(row):
            return

        # Process row based on current section
        if self.current_section == IBCsvSection.FINANCIAL_INSTRUMENT:
            self._process_financial_instrument_row(row)
        elif self.current_section == IBCsvSection.TRADES:
            self._process_trades_row(row)
        elif self.current_section == IBCsvSection.DIVIDENDS:
            self._process_dividends_row(row)
        elif self.current_section == IBCsvSection.WITHHOLDING_TAX:
            self._process_withholding_tax_row(row)
        # OTHER sections are ignored

    def _detect_section_transition(self, row: list[str]) -> bool:
        """Detect if this row represents a section transition."""
        # Only treat as section transition if it's a header row
        # IB CSV format: Section Name, Header, Column1, Column2, ...
        if len(row) < self.MIN_ROW_LENGTH or row[1] != CSV_HEADER_MARKER:
            return False

        section_name = row[0]

        if section_name == "Financial Instrument Information":
            self._transition_to_financial_instruments(row)
            return True
        elif section_name == "Trades":
            self._transition_to_trades(row)
            return True
        elif section_name == "Dividends":
            self._transition_to_dividends(row)
            return True
        elif section_name == "Withholding Tax":
            self._transition_to_withholding_tax(row)
            return True
        else:
            # Found a header for a section we don't process (e.g. "Interest", "Fees", etc.)
            self._transition_to_other(row)
            return True

    def _transition_to_financial_instruments(self, row: list[str]) -> None:
        """Transition to Financial Instrument section."""
        self.current_section = IBCsvSection.FINANCIAL_INSTRUMENT
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_HEADER_MARKER:
            try:
                self.financial_context.process_header(row, self.current_row_number)
                self.found_financial_instrument_header = True
            except Exception as e:
                self.logger.warning("Failed to process financial instrument header: %s, row: %s", e, row)
                # Continue processing even if header validation fails

    def _transition_to_trades(self, row: list[str]) -> None:
        """Transition to Trades section."""
        self.current_section = IBCsvSection.TRADES
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_HEADER_MARKER:
            self.trades_context.process_header(row, self.current_row_number)

    def _transition_to_dividends(self, row: list[str]) -> None:
        """Transition to Dividends section."""
        self.current_section = IBCsvSection.DIVIDENDS
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_HEADER_MARKER:
            self.dividends_context.process_header(row, self.current_row_number)

    def _transition_to_withholding_tax(self, row: list[str]) -> None:
        """Transition to Withholding Tax section."""
        self.current_section = IBCsvSection.WITHHOLDING_TAX
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_HEADER_MARKER:
            self.withholding_tax_context.process_header(row, self.current_row_number)

    def _transition_to_other(self, _row: list[str]) -> None:
        """Transition to ignored/other section."""
        self.current_section = IBCsvSection.OTHER
        # We don't need to process headers or data for ignored sections

    def _process_financial_instrument_row(self, row: list[str]) -> None:
        """Process row in Financial Instrument section."""
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_DATA_MARKER:
            self.financial_context.process_data_row(row, self.current_row_number)

    def _process_trades_row(self, row: list[str]) -> None:
        """Process row in Trades section."""
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_DATA_MARKER:
            self.trades_context.process_data_row(row, self.current_row_number)

    def _process_dividends_row(self, row: list[str]) -> None:
        """Process row in Dividends section."""
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_DATA_MARKER:
            self.dividends_context.process_data_row(row, self.current_row_number)

    def _process_withholding_tax_row(self, row: list[str]) -> None:
        """Process row in Withholding Tax section."""
        if len(row) >= self.MIN_ROW_LENGTH and row[1] == CSV_DATA_MARKER:
            self.withholding_tax_context.process_data_row(row, self.current_row_number)

    def finalize(self) -> IBCsvData:
        """Finalize processing and return collected data."""
        # Validation
        if not self.found_financial_instrument_header:
            raise FileProcessingError("Missing 'Financial Instrument Information' header in CSV")

        if self.require_trades_section and not self.trades_context.headers_found:
            raise FileProcessingError("No Trades section found in the IB export file")

        metadata = {
            "processed_trades": self.trades_context.processed_count,
            "invalid_trades": self.trades_context.invalid_trades,
            "processed_dividends": self.dividends_context.processed_count,
            "processed_withholding_taxes": self.withholding_tax_context.processed_count,
            "security_processed_count": self.financial_context.security_processed_count,
        }

        self.logger.info(
            "Extracted security data for %s symbols (%s with country data)",
            len(self.security_info),
            self.financial_context.security_processed_count,
        )
        self.logger.info(
            "Collected %s trades, %s dividends and %s withholding taxes",
            self.trades_context.processed_count,
            self.dividends_context.processed_count,
            self.withholding_tax_context.processed_count,
        )
        if self.trades_context.invalid_trades > 0:
            self.logger.warning(
                "Skipped %s invalid trades (missing symbol or datetime)",
                self.trades_context.invalid_trades,
            )

        return IBCsvData(
            security_info=self.security_info,
            raw_trade_data=self.raw_trade_data,
            raw_dividend_data=self.raw_dividend_data,
            raw_withholding_tax_data=self.raw_withholding_tax_data,
            metadata=metadata,
        )
