# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shares reporting tool is a financial application that processes Interactive Brokers CSV reports to generate tax reporting data for capital gains calculations. It matches buy/sell transactions within the same day to calculate capital gains and generates Excel reports with currency conversion.

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

### Clean Architecture with Domain-Driven Design

The project follows **professional layered architecture** with **Domain-Driven Design** principles:

#### **Layered Architecture**
- **Domain Layer** (`src/shares_reporting/domain/`): Core business entities and rules
  - `value_objects.py` - TradeDate, Currency, Company, TradeType
  - `entities.py` - TradeAction, TradeCycle, CapitalGainLine
  - `accumulators.py` - CapitalGainLineAccumulator, TradePartsWithinDay
  - `collections.py` - Type aliases and collections
- **Application Layer** (`src/shares_reporting/application/`): Business logic and orchestration
  - `extraction.py` - CSV data parsing and domain object creation
  - `transformation.py` - Capital gains calculation and trade matching
  - `persisting.py` - Excel/CSV report generation with formulas
- **Infrastructure Layer** (`src/shares_reporting/infrastructure/`): External concerns
  - `config.py` - Configuration management and currency exchange rates
- **Presentation Layer** (`src/shares_reporting/main.py`): Application entry point and orchestration

### Core Business Logic Pipeline
The system processes trades in this pipeline:
1. **Extraction**: Parse Interactive Brokers CSV files into domain objects
2. **Transformation**: Group trades by company/currency, match buys/sells chronologically using FIFO within daily buckets
3. **Persistence**: Generate Excel reports with calculated capital gains + CSV files for unmatched shares

### Domain Model Architecture
Rich domain models with proper separation of concerns:
- **Value Objects** (Immutable): TradeDate, Currency, Company, TradeType with validation
- **Entities** (Rich): TradeAction, TradeCycle, CapitalGainLine with business behavior
- **Accumulators**: CapitalGainLineAccumulator, TradePartsWithinDay for complex calculations
- **Collections**: Type aliases for better code readability and maintainability

## Configuration Management

- Uses Python's `configparser` for INI file handling
- Configuration files: `config.ini` (production) and `tests/config.ini` (testing)
- Supports target currency specification and exchange rate management
- Currency exchange rates should be updated annually (e.g., from your national central bank or financial institution)

## Data Flow

**Input**: Interactive Brokers CSV reports placed in `/resources/source/`
**Processing**: Domain-driven transformation pipeline with currency conversion
**Output**: Excel reports with formulas in `/resources/result/` + CSV leftover files

## Testing Strategy

### **Comprehensive Test Suite**
The project follows **professional testing best practices** with **high unit test coverage**:

#### **Test Structure** (Mirrors Package Structure)
```
tests/
├── domain/                     # Domain layer unit tests
│   ├── test_value_objects.py   # 29 tests - Value objects and validation
│   ├── test_collections.py    # 15 tests - Type aliases and collections
│   ├── test_accumulators.py   # 56 tests - Business accumulators
│   └── test_entities.py       # 44 tests - Core entities
├── application/                # Application layer tests
│   └── test_extraction.py     # CSV parsing edge cases
├── infrastructure/             # Infrastructure layer tests
│   └── test_config.py         # Configuration management
├── test_shares.py             # Integration tests (existing)
└── test_reporting.py          # End-to-end tests (existing)
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
poetry run pytest tests/test_shares.py tests/test_reporting.py
```

#### **Testing Best Practices**
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Edge Cases**: Comprehensive error handling and boundary conditions
- **Test Coverage**: High coverage of business logic and validation
- **Descriptive Naming**: Clear test names that document behavior
- **Debugging**: Use `breakpoint()` or `import pdb; pdb.set_trace()`

## Development Environment

- **Python 3.11+ required** (f-string usage and modern features)
- **Poetry for dependency management** (recommended approach)
- **Professional package structure** with `src/` layout
- **Clean Architecture** with Domain-Driven Design
- **Type hints extensively used** throughout codebase
- **pytest framework** with comprehensive unit and integration tests
- **Modern tooling**: Coverage reporting, professional packaging

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
│       │   └── collections.py    # Type aliases and utilities
│       ├── application/      # Application layer
│       │   ├── __init__.py
│       │   ├── extraction.py    # CSV data parsing
│       │   ├── transformation.py # Capital gains calculation
│       │   └── persisting.py    # Excel/CSV generation
│       └── infrastructure/    # Infrastructure layer
│           ├── __init__.py
│           └── config.py        # Configuration management
├── tests/                  # Test suite
│   ├── domain/             # Domain layer unit tests
│   │   ├── test_value_objects.py
│   │   ├── test_collections.py
│   │   ├── test_accumulators.py
│   │   └── test_entities.py
│   ├── application/        # Application layer tests
│   │   └── test_extraction.py
│   ├── infrastructure/     # Infrastructure layer tests
│   │   └── test_config.py
│   ├── test_shares.py       # Integration tests (existing)
│   ├── test_reporting.py    # End-to-end tests (existing)
│   └── test_data.py         # Test fixtures (existing)
├── resources/              # Data directories
│   ├── source/             # Input CSV files
│   └── result/             # Generated reports
├── pyproject.toml          # Poetry configuration and dependencies
├── config.ini              # Application configuration
├── README.md               # Project documentation
└── CLAUDE.md              # This file - Claude Code guidance
```