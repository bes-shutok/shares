# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shares reporting tool is a financial application that processes Interactive Brokers CSV reports to generate tax reporting data for Portugal. It matches buy/sell transactions within the same day to calculate capital gains and generates Excel reports with currency conversion.

## Development Commands

### Running the Application
```bash
# Using Poetry (recommended)
poetry run python ./reporting.py

# Using Poetry shell
poetry shell
python ./reporting.py

# Ensure config.ini has all required currency exchange pairs
# Update source files in /resources/source folder
```

### Environment Setup
```bash
# Install Poetry (one-time setup)
See https://python-poetry.org/docs/#installing-with-pipx

# Install all dependencies (production + development)
poetry install

# Install only production dependencies
poetry install --only main

# Activate virtual environment
poetry shell

# Exit virtual environment
exit
```

### Testing
```bash
# Using Poetry (recommended)
poetry run pytest                    # Run all tests
poetry run pytest -k <keyword>       # Run tests matching keyword
poetry run pytest -vvl              # Verbose output with all variables
poetry run pytest --cov=.           # Run with coverage
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

### Layered Architecture Pattern
- **Domain Layer** (`domain.py`): Rich domain models with business logic (TradeAction, TradeCycle, CapitalGainLine)
- **Data Access Layer** (`extraction.py`): CSV parsing and data loading utilities
- **Business Logic Layer** (`transformation.py`): Capital gains calculations and trade matching
- **Presentation Layer** (`persisting.py`): Excel/CSV report generation with formulas
- **Configuration Layer** (`config.py`): Settings and currency exchange rate management

### Core Business Logic
The system processes trades in this pipeline:
1. **Extraction**: Parse Interactive Brokers CSV files into domain objects
2. **Transformation**: Group trades by company/currency, match buys/sells chronologically using FIFO within daily buckets
3. **Persistence**: Generate Excel reports with calculated capital gains + CSV files for unmatched shares

### Domain Model
Key domain objects use NamedTuple/dataclass patterns:
- `TradeAction`: Individual buy/sell transactions
- `TradeCycle`: Collection of trades for a company
- `CapitalGainLine`: Matched buy/sell pairs for tax reporting
- `CurrencyCompany`: Composite key for grouping trades
- `TradePartsWithinDay`: Daily aggregation structure

## Configuration Management

- Uses Python's `configparser` for INI file handling
- Configuration files: `config.ini` (production) and `tests/config.ini` (testing)
- Supports target currency specification and exchange rate management
- Currency exchange rates should be updated annually (e.g., from Banco de Portugal)

## Data Flow

**Input**: Interactive Brokers CSV reports placed in `/resources/source/`
**Processing**: Domain-driven transformation pipeline with currency conversion
**Output**: Excel reports with formulas in `/resources/result/` + CSV leftover files

## Testing Notes

- Tests use pytest framework with fixtures in `test_data.py`
- Integration tests cover end-to-end workflows
- For debugging: use `breakpoint()` or `import pdb; pdb.set_trace()`
- Test names follow pytest conventions with descriptive function names

## Development Environment

- **Python 3.11+ required** (f-string usage and modern features)
- **Poetry for dependency management** (recommended approach)
- **Flat module structure** with direct Python module imports
- **Type hints extensively used** throughout codebase
- **pytest framework** with comprehensive test coverage
- **Modern tooling**: Coverage reporting, linting, formatting support

## Project Structure

```
shares-reporting/
├── pyproject.toml          # Poetry configuration and dependencies
├── config.ini              # Application configuration
├── reporting.py            # Main application entry point
├── domain.py               # Domain models and business logic
├── extraction.py           # Data parsing utilities
├── transformation.py       # Business logic for calculations
├── persisting.py           # Report generation utilities
├── config.py               # Configuration management
├── tests/                  # Test suite
│   ├── test_data.py        # Test fixtures
│   ├── test_reporting.py   # Integration tests
│   └── test_shares.py      # Unit tests
├── resources/              # Data directories
│   ├── source/             # Input CSV files
│   └── result/             # Generated reports
└── README.md               # Project documentation
```