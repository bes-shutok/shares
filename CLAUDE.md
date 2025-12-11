# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shares reporting tool is a financial application that processes Interactive Brokers CSV reports to generate tax reporting data for capital gains and dividend income calculations. It matches buy/sell transactions within the same day to calculate capital gains, processes dividend payments with tax information, and generates comprehensive Excel reports with currency conversion.

## Development Commands

### Running the Application
```bash
# Using Poetry (recommended)
poetry run shares-reporting

# Using Poetry shell
poetry shell
shares-reporting

# Direct execution (alternative)
poetry run python ./src/shares_reporting/main.py

# Ensure config.ini has all required currency exchange pairs
# Update source files in /resources/source folder
```

### Environment Setup
```bash
# Install Poetry (one-time setup)
See https://python-poetry.org/docs/#installing-with-pipx

# Configure Poetry to create virtual environment in-project
poetry config virtualenvs.in-project true

# Install all dependencies (production + development)
poetry install

# Install only production dependencies
poetry install --only main

# Activate virtual environment
poetry shell

# Exit virtual environment
exit
```

### Dependency Management
```bash
# Add new dependency
poetry add <package_name>

# Add development dependency
poetry add --group dev <package_name>

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree

# Check for outdated dependencies
poetry outdated
```

## Architecture
The project follows **professional layered architecture** with **Domain-Driven Design** principles:

#### **Layered Architecture**
- **Domain Layer** (`src/shares_reporting/domain/`): Core business entities and rules
  - `value_objects.py` - TradeDate, Currency, Company, TradeType
  - `entities.py` - TradeAction, TradeCycle, CapitalGainLine
  - `accumulators.py` - CapitalGainLineAccumulator, TradePartsWithinDay
  - `collections.py` - Type aliases and collections
  - `constants.py` - Domain constants
  - `exceptions.py` - Domain exceptions
- **Application Layer** (`src/shares_reporting/application/`): Business logic and orchestration
  - `extraction/` - CSV data parsing package
    - `models.py` - Data structures
    - `contexts.py` - Parsing contexts
    - `state_machine.py` - Parsing state machine
    - `processing.py` - Core processing logic
  - `transformation.py` - Capital gains calculation and trade matching
  - `persisting.py` - Excel report generation with formulas (capital gains + dividend income)
- **Infrastructure Layer** (`src/shares_reporting/infrastructure/`): External concerns
  - `config.py` - Configuration management and currency exchange rates
  - `isin_country.py` - ISIN to country resolution
  - `logging_config.py` - Logging configuration
  - `validation.py` - Input validation
- **Presentation Layer** (`src/shares_reporting/main.py`): Application entry point and orchestration

### Core Business Logic Pipeline

#### **Data Processing Flow**
The system processes data through a sophisticated tax-compliant pipeline:
1. **Extraction**: `parse_ib_export_all()` parses Interactive Brokers CSV files into domain objects (trades + dividends + security info)
2. **Transformation**: `calculate_fifo_gains()` implements the core capital gains algorithm
3. **Persistence**: `generate_tax_report()` creates Excel reports + `export_rollover_file()` for inventory rollover

#### **CSV Extraction Architecture**

The `extraction` package uses a **State Machine** pattern to parse complex Interactive Brokers CSV files:

**Components:**
- **`IBCsvStateMachine`**: Orchestrates the parsing process, transitioning between file sections.
- **Contexts** (`contexts.py`): Specialized handlers for each CSV section:
  - `FinancialInstrumentContext`: Extracts security info (ISIN, Country).
  - `TradesContext`: Parses trade executions.
  - `DividendsContext`: Extracts dividend records.
  - `WithholdingTaxContext`: Parses tax records.
- **Models** (`models.py`): Data structures for raw extracted data (`IBCsvData`, `IBCsvSection`).

**Flow:**
1. `IBCsvStateMachine` reads the CSV row by row.
2. Detects section headers (e.g., "Financial Instrument Information", "Trades").
3. Delegates row processing to the active `BaseSectionContext` subclass.
4. Aggregates results into `IBCsvData` for downstream processing.

#### **FIFO Algorithm Deep Dive**

The `calculate_fifo_gains()` function implements sophisticated capital gains calculation:

**State Machine Design:**
- **Company-Level Processing**: Each company/currency processed independently
- **Daily Bucketing**: `split_by_days()` ensures tax compliance by date grouping
- **FIFO Matching**: `capital_gains_for_company()` with `TradePartsWithinDay` queues
- **Partial Matching**: `allocate_to_gain_line()` handles quantity differences
- **Leftover Management**: `redistribute_unmatched_trades()` for inventory rollover to next year

**Key Components:**
- **`CapitalGainLineAccumulator`**: Builder pattern for capital gain calculations
- **`TradePartsWithinDay`**: FIFO queue ensuring chronological trade matching
- **State Transitions**: Each accumulator tracks buy/sell completion states
- **Validation Rules**: Ensures quantities match and business constraints are met

#### **Troubleshooting Guide**

**Common Issues and Solutions:**

1. **Empty Rollover Files**
   - **Issue**: No unmatched securities found
   - **Cause**: Perfect FIFO matching achieved
   - **Solution**: This is normal behavior, indicates successful processing

2. **Large Rollover Files**
   - **Issue**: Many unmatched securities remain
   - **Cause**: Unbalanced buy/sell quantities, inventory rollover to next tax year
   - **Solution**: Check IB export completeness, verify date ranges, expect rollover for next year's calculations

3. **Date Validation Errors**
   - **Issue**: Trade date outside tax year expected range
   - **Cause**: CSV contains transactions from wrong period
   - **Solution**: Verify source file covers correct tax year, filter data if needed

4. **Currency Conversion Errors**
   - **Issue**: Missing exchange rate for currency pair
   - **Cause**: New currency in data not in config.ini
   - **Solution**: Add exchange rates to configuration file

5. **ISIN Validation Failures**
   - **Issue**: Unrecognized financial instruments
   - **Cause**: Corrupted CSV or missing security information
   - **Solution**: Verify IB export format, check Financial Instrument Information section

**Debugging Strategies:**
- **Enable Debug Logging**: Configure logging level to DEBUG in main.py
- **Step-by-Step Processing**: Run small test files first
- **Data Validation**: Check IB export file completeness and format
- **Configuration Review**: Verify currency pairs and exchange rates are current

**Performance Considerations:**
- **Large Datasets**: Processing time scales with transaction count
- **Memory Usage**: All data loaded in memory for state machine design
- **File Size Limits**: Very large CSV files (>100MB) may need splitting

### Domain Model Architecture
Rich domain models with proper separation of concerns:
- **Value Objects** (Immutable): TradeDate, Currency, Company, TradeType with validation
- **Entities** (Rich): TradeAction, TradeCycle, CapitalGainLine with business behavior
- **Accumulators**: CapitalGainLineAccumulator, TradePartsWithinDay for complex calculations
- **Collections**: Type aliases for trades, capital gains, and dividend income data structures

## Configuration Management

- Uses Python's `configparser` for INI file handling
- Configuration files: `config.ini` (production) and `tests/config.ini` (testing)
- Both configs have identical structure with three sections:
  - **[COMMON]**: Target currency specification
  - **[EXCHANGE RATES]**: Currency conversion rates (different values for prod/test)
  - **[SECURITY]**: Validation limits (file size, ticker length, allowed extensions, etc.)
- Exchange rates should be updated annually (e.g., from your national central bank)
- Security settings use defaults from code if missing from config file

## Excel Report Features

The application generates professional Excel reports with:

### Capital Gains Section
- Detailed buy/sell transaction matching with FIFO methodology
- Automatic currency conversion with exchange rate tables
- Country of source detection from ISIN data

### Dividend Income Section ("CAPITAL INVESTMENT INCOME")
- Complete dividend reporting with tax information
- Both converted and original currency amounts displayed
- Symbol, Currency, ISIN, and country information
- Gross amount, withholding tax, and net amount calculations

### Report Structure
- **Column Headers**: Clear, descriptive headers with line breaks for readability
- **Currency Conversion**: Automatic conversion using configured exchange rates
- **Formulas**: Excel formulas for dynamic calculations
- **Auto-sizing**: Column widths automatically adjusted for content

## Data Flow

**Input**: Interactive Brokers CSV reports placed in `/resources/source/`
**Processing**: Domain-driven transformation pipeline with currency conversion and ISIN mapping
**Output**: Comprehensive Excel reports with capital gains, dividend income, and currency conversion tables in `/resources/result/` + unmatched securities rollover file for next year's calculations

## Testing Strategy

### **Comprehensive Test Suite**
The project follows **professional testing best practices** with **high unit test coverage**:

#### **Test Structure** (Mirrors Package Structure)
```
tests/
├── domain/                     # Domain layer unit tests
│   ├── test_value_objects.py   # Value objects and validation
│   ├── test_collections.py    # Type aliases and collections
│   ├── test_accumulators.py   # Business accumulators
│   └── test_entities.py       # Core entities
├── application/                # Application layer tests
│   ├── test_extraction.py     # CSV parsing edge cases
│   ├── test_dividend_extraction.py # Dividend income extraction and processing
│   ├── test_isin_extraction.py # ISIN mapping and financial instrument processing
│   └── test_raw_ib_export_parsing.py # Interactive Brokers CSV parsing
├── infrastructure/             # Infrastructure layer tests
│   └── test_config.py         # Configuration management
├── test_shares_raw_ib.py             # Integration tests (existing)
└── test_reporting_raw_ib.py          # End-to-end tests (existing)
```

#### **Testing Commands**
```bash
# Run all tests
poetry run pytest

# Run tests by layer
poetry run pytest tests/domain/           # Domain layer unit tests
poetry run pytest tests/application/        # Application layer tests
poetry run pytest tests/infrastructure/     # Infrastructure tests

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run only unit tests (excluding integration)
poetry run pytest tests/domain/ tests/application/ tests/infrastructure/

# Run existing integration tests
poetry run pytest tests/test_shares_raw_ib.py tests/test_reporting_raw_ib.py
```

#### **Testing Best Practices**
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Edge Cases**: Comprehensive error handling and boundary conditions
- **Test Coverage**: High coverage of business logic and validation
- **Descriptive Naming**: Clear test names that document behavior
- **Debugging**: Use `breakpoint()` or `import pdb; pdb.set_trace()`



## Code Quality Standards

### Linting and Formatting
- **Ruff** is the primary linter and formatter (configured in `pyproject.toml`)
- **Target**: Python 3.13 (`target-version = "py313"`)
- **Line length**: 120 characters maximum
- **Enabled rulesets**: `E`, `F`, `UP`, `B`, `SIM`, `I`, `N`, `ARG`, `FA`, `DTZ`, `PTH`, `TD`, `FIX`, `RSE`, `S`, `C4`, `PT`, `D`, `PL`
- **Docstring convention**: Google-style (`pydocstyle`)

### Documentation Best Practices

#### When to Write Docstrings
- **Always document**:
  - Public modules (`__init__.py`, top-level modules)
  - Public classes and their `__init__` methods
  - Public functions and methods with complex logic or non-obvious behavior
  - Functions with multiple parameters or return values

- **Skip docstrings for**:
  - Self-explanatory property getters/setters (e.g., `def get_currency(self): return self.currency`)
  - Trivial magic methods like `__repr__` when the implementation is obvious
  - Private methods (`_method_name`) when the name and implementation are clear
  - Test functions (docstrings optional in tests per `pyproject.toml`)

#### Docstring Style (Google Convention)
```python
def complex_function(param1: str, param2: int) -> dict:
    """Brief one-line summary ending with a period.

    Extended description if needed. Explain the purpose, algorithm,
    or any non-obvious behavior.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When validation fails.
    """
```

#### Package `__init__.py` Docstrings
Use multi-line format with summary + description:
```python
"""Package name for specific purpose.

Extended description explaining what the package contains,
its responsibilities, and key modules or functionality.
"""
```

### Code Style Guidelines
- **Type hints**: Use modern syntax (`X | Y` instead of `Union[X, Y]`) with `from __future__ import annotations`
- **Imports**: Sorted automatically by Ruff (isort)
- **Magic numbers**: Replace with named constants (except in tests)
- **Datetime**: Use `datetime.UTC` instead of `timezone.utc` (Python 3.11+)
- **Path handling**: Use `pathlib.Path` instead of `os.path`
- **Logging**: Use lazy formatting (`logger.info("Message: %s", value)` not f-strings)

### Complexity Management
- Functions with high complexity (`PLR0912`, `PLR0915`) should be refactored when possible
- If refactoring is too risky, use explicit `# noqa: PLR0912, PLR0915` with a comment explaining why
- Avoid deeply nested logic; extract helper functions

## Project Structure

```
shares-reporting/
├── src/                     # Source code (src layout)
│   └── shares_reporting/
│       ├── __init__.py        # Package exports
│       ├── main.py           # Application entry point
│       ├── domain/           # Domain layer
│       │   ├── __init__.py
│       │   ├── value_objects.py   # TradeDate, Currency, Company, TradeType
│       │   ├── entities.py      # TradeAction, TradeCycle, CapitalGainLine
│       │   ├── accumulators.py   # CapitalGainLineAccumulator, TradePartsWithinDay
│       │   ├── collections.py    # Type aliases and utilities
│       │   ├── constants.py      # Domain constants
│       │   └── exceptions.py     # Domain exceptions
│       ├── application/      # Application layer
│       │   ├── __init__.py
│       │   ├── extraction/      # CSV data parsing package
│       │   │   ├── __init__.py
│       │   │   ├── models.py
│       │   │   ├── contexts.py
│       │   │   ├── state_machine.py
│       │   │   └── processing.py
│       │   ├── transformation.py # Capital gains calculation
│       │   └── persisting.py    # Excel/CSV generation
│       └── infrastructure/    # Infrastructure layer
│           ├── __init__.py
│           ├── config.py        # Configuration management
│           ├── isin_country.py  # ISIN to country resolution
│           ├── logging_config.py # Logging configuration
│           └── validation.py    # Input validation
├── tests/                  # Test suite
│   ├── domain/             # Domain layer unit tests
│   │   ├── test_value_objects.py
│   │   ├── test_collections.py
│   │   ├── test_accumulators.py
│   │   └── test_entities.py
│   ├── application/        # Application layer tests
│   │   ├── test_extraction.py
│   │   ├── test_dividend_extraction.py
│   │   ├── test_isin_extraction.py
│   │   └── test_raw_ib_export_parsing.py
│   ├── infrastructure/     # Infrastructure layer tests
│   │   └── test_config.py
│   ├── test_shares_raw_ib.py       # Integration tests (existing)
│   ├── test_reporting_raw_ib.py    # End-to-end tests (existing)
│   └── test_data.py         # Test fixtures (existing)
├── resources/              # Data directories
│   ├── source/             # Input CSV files
│   └── result/             # Generated reports
├── pyproject.toml          # Poetry configuration and dependencies
├── config.ini              # Application configuration
├── README.md               # Project documentation
└── CLAUDE.md              # This file - Claude Code guidance
```
