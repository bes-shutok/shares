# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shares reporting tool is a financial application that processes Interactive Brokers CSV reports to generate tax reporting data for capital gains and dividend income calculations. It matches buy/sell transactions within the same day to calculate capital gains, processes dividend payments with tax information, and generates comprehensive Excel reports with currency conversion.

## Development Commands

### Running the Application
```bash
# Using UV (recommended)
uv run shares-reporting

# Activate virtual environment
source .venv/bin/activate
shares-reporting

# Direct execution (alternative)
uv run python ./src/shares_reporting/main.py

# Ensure config.ini has all required currency exchange pairs
# Update source files in /resources/source folder
```

### Environment Setup
```bash
# Install UV (one-time setup)
See https://docs.astral.sh/uv/getting-started/installation/

# Install all dependencies (production + development)
uv sync --extra dev

# Install only production dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Exit virtual environment
exit
```

### Running Commands
- Use `uv run` for the local application (`shares-reporting`) - the project is not published to PyPI
- Use `uvx` for faster execution of installed tools (pytest, ruff) - tools installed in .venv via uv sync
- Use `uv` for dependency management and setup commands

### Development Workflow Commands
```bash
# Quick development cycle
uvx pytest                     # Run tests (fast)
uvx ruff check . --fix && uvx ruff format .  # Lint and format (fast)
uv run shares-reporting       # Run the application

# Dependency management
uv add requests               # Add production dependency
uv add --dev pytest-mock     # Add development dependency
uv lock --upgrade            # Update dependencies

# Testing variations
uvx pytest -k "test_specific"    # Run specific tests
uvx pytest --cov=src --cov-report=html  # Run with coverage report
uvx pytest tests/domain/    # Run specific test modules
```

### Dependency Management
```bash
# Add new dependency
uv add <package_name>

# Add development dependency
uv add --dev <package_name>

# Update dependencies
uv lock --upgrade

# Show dependency tree
uv tree

# Check for outdated dependencies
uv pip list --outdated
```

### Common Mistakes to Avoid
- `uvx shares-reporting` - ❌ Won't work (project is not published to PyPI)
- `uvx run shares-reporting` - ❌ Installs 'run' package, not what you want
- `uv run shares-reporting` - ✅ Correct way to run the local application

**Key point**: This project uses a local entry point defined in `pyproject.toml`, not a published PyPI package.

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
│   ├── test_raw_ib_export_parsing.py # Interactive Brokers CSV parsing
│   ├── test_placeholder_buys.py # Placeholder buy logic for capital gains
│   ├── test_missing_isin_behavior.py # Missing ISIN handling behavior
│   ├── test_dividend_missing_isin.py # Dividend processing with missing ISIN
│   ├── test_dividend_edge_cases.py # Dividend edge cases and validation
│   ├── test_dividend_integration.py # Dividend processing integration tests
│   └── test_dividend_persisting.py # Dividend Excel report generation
├── infrastructure/             # Infrastructure layer tests
│   ├── test_config.py         # Configuration management
│   └── test_isin_country.py   # ISIN to country resolution
├── test_shares_raw_ib.py             # Integration tests (existing)
└── test_reporting_raw_ib.py          # End-to-end tests (existing)
```

#### **Testing Commands**
```bash
# Run all tests
uvx pytest

# Run tests by layer
uvx pytest tests/domain/           # Domain layer unit tests
uvx pytest tests/application/        # Application layer tests
uvx pytest tests/infrastructure/     # Infrastructure tests

# Run with coverage
uvx pytest --cov=src --cov-report=html

# Run only unit tests (excluding integration)
uvx pytest tests/domain/ tests/application/ tests/infrastructure/

# Run existing integration tests
uvx pytest tests/test_shares_raw_ib.py tests/test_reporting_raw_ib.py
```

#### **Testing Best Practices**
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Edge Cases**: Comprehensive error handling and boundary conditions
- **Test Coverage**: High coverage of business logic and validation
- **Descriptive Naming**: Clear test names that document behavior
- **Debugging**: Use `breakpoint()` or `import pdb; pdb.set_trace()`

### Development Best Practices

#### Incremental Development with Testing
**Test-driven approach for complex changes**:
1. **Write failing tests first** to understand expected behavior
2. **Implement changes** with comprehensive test coverage
3. **Run the full test suite** to ensure no regressions
4. **Review and clean up** low-value tests after functionality works

#### API Design Consistency
**Maintain consistent patterns across similar functions**:
```python
# ✅ GOOD - Consistent parameter patterns across context methods
def process_header(self, row: list[str], row_number: int) -> None:
def process_data_row(self, row: list[str], row_number: int) -> None:

# ✅ GOOD - Consistent error message patterns
raise FileProcessingError("Row %d: Invalid %s format", row_number, section_name)
```

#### Code Review Checklist
**Before considering code complete, verify**:
- [ ] All required parameters are truly required (no misleading defaults)
- [ ] Error messages include sufficient context (row numbers, problematic data)
- [ ] Exception chaining preserves original error information  
- [ ] Logging uses parameterized format consistently
- [ ] Fail fast logic is applied appropriately (missing vs invalid data)
- [ ] Tests provide real value and test meaningful edge cases
- [ ] API usage is correct (high-level vs low-level functions)
- [ ] No pytest fixture imports (tmp_path, capsys, caplog, monkeypatch, request)
- [ ] No unused imports (fix Ruff F401 errors unless proven false positive)
- [ ] Path imports only when actually needed (not for injected fixtures)

#### Documentation Maintenance
**Keep documentation current with code changes**:
- Update CLAUDE.md when new patterns emerge
- Include examples of both good and bad practices
- Document decision rationale for architectural choices
- Maintain clear separation between testing vs script guidelines



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
- **Error Messages**: Use f-strings for exception messages (`raise ValueError(f"Invalid value: {value}")`)

#### Method Parameter Design Principles
**Required vs Optional Parameters**: 
- **Required**: Use when data is essential for correct operation (e.g., `row_number` for error context)
- **Optional**: Use only when a sensible default exists and doesn't compromise functionality
- **Avoid defaults of 0** for identifiers/indices that need real values

```python
# ✅ GOOD - Required parameter for essential data
def process_data_row(self, row: list[str], row_number: int) -> None:

# ❌ AVOID - Default value for essential context
def process_data_row(self, row: list[str], row_number: int = 0) -> None:
```

#### Testing Principles

**Test Location and Structure**:
- **Tests**: Use `tests/` directory with pytest naming conventions (`test_*.py`)
- **Scripts**: Use for one-time utilities or demonstrations, not automated testing
- **Structure**: Mirror package structure (`tests/domain/`, `tests/application/`, etc.)

#### Pytest Fixtures and Import Guidelines

**Critical Rule**: Do not import pytest fixtures - they are injected automatically by name.

**Common Pytest Fixtures (No Import Required)**:
```python
# ✅ GOOD - Use directly without imports
def test_something(tmp_path):
    # tmp_path is injected automatically
    test_file = tmp_path / "test.txt"
    
def test_logging(caplog):
    # caplog is injected automatically  
    assert "expected message" in caplog.text

def test_output(capsys):
    # capsys is injected automatically
    captured = capsys.readouterr()
```

**Available Fixtures Without Import**:
- `tmp_path` - Filesystem operations (pathlib.Path)
- `capsys` - Capture stdout/stderr
- `caplog` - Capture logging output
- `monkeypatch` - Patch environment/attributes
- `request` - Test context and metadata

**Path Import Rules**:
```python
# ✅ GOOD - Use tmp_path directly, no Path import needed
def test_with_file(tmp_path):
    file_path = tmp_path / "test.csv"
    file_path.write_text("content")

# ✅ GOOD - Import Path only for type annotations
from pathlib import Path
def process_file(file_path: Path) -> None:
    pass

def test_function(tmp_path):  # No import needed
    process_file(tmp_path / "test.txt")

# ❌ AVOID - Unnecessary Path import
from pathlib import Path
def test_with_file(tmp_path):
    file_path = Path(tmp_path) / "test.txt"  # tmp_path is already Path
```

**Import Cleanliness Rules**:
- **Remove unused imports**: If Ruff reports F401, delete the import unless justified
- **Assume Ruff is correct**: Fix the code, not the linter, unless proven false positive
- **Only import when used**:
  - ✅ When instantiating: `Path("some/path")`
  - ✅ When used in type annotations: `def func(file_path: Path) -> None`
  - ❌ When using injected fixtures: `def test(tmp_path):` (no import needed)

**Prefer Built-in Fixtures Over Manual Setup**:
```python
# ✅ GOOD - Use pytest's built-in tmp_path
def test_file_operations(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

# ❌ AVOID - Manual tempfile handling
import tempfile
def test_file_operations():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # More complex and error-prone
```

**Test Value Assessment**:
Ask these questions for every test:
1. **Does it test meaningful business logic** that could break in production?
2. **Does it test real edge cases** from actual data/usage?
3. **Is it testing something not already covered** by other tests?
4. **Would a failure provide actionable information** for debugging?

**Low-Value Test Patterns to Avoid**:
- Testing zero amounts (if positives work, zeros work too)
- Testing basic string parsing that should work anyway
- Testing simple symbol matching (AAPL/MSFT basics)
- Testing very small decimal amounts without business meaning
- Testing trivial cases that would be caught by other tests

**High-Value Test Patterns to Include**:
- Complex IB CSV description formats
- Missing data scenarios with error indicators  
- Tax calculation and matching logic
- Integration flows between components
- Error handling and validation paths
- Performance with realistic datasets
- Real edge cases from actual exports

**API Usage in Tests**:
- **Use appropriate functions**: Don't use high-level APIs when you need raw data access
- **Understand function return types**: Check if functions return processed or raw data
- **Test at the right level**: Unit test individual functions, integration test complete flows

#### Preferred Logging and Error Message Format

**Logging Messages**: Use parameterized format for logging to improve maintainability, debugging, and performance:

```python
# ✅ GOOD - Parameterized format for logging
logger.debug("Row %d: Created placeholder buy for %s: quantity=%s, date=%d-01-01, price=0", 
              row_number, company.ticker, total_sold, PLACEHOLDER_YEAR)

logger.error("Row %d: Invalid dividend amount for %s: expected positive, got %s", 
             row_number, symbol, amount)

# ❌ AVOID - Inline interpolation in logging
logger.debug(f"Created buy for {company} with quantity {qty}")
```

**Exception Messages**: Use f-strings for exception messages since Python exceptions don't support parameterized formatting:

```python
# ✅ GOOD - f-strings for exceptions
raise ValueError(f"Row {row}: Invalid header format: {header}")
raise DataValidationError(f"Taxes ({self.total_taxes}) cannot exceed gross amount ({self.gross_amount})")

# ❌ AVOID - Parameterized format in exceptions (won't work as expected)
try:
    raise ValueError("Invalid value: %s", value)  # This won't format correctly
except TypeError:
    # The above will fail because ValueError expects a single string argument
    pass
```

**Benefits of Parameterized Format**:
- **Easier debugging**: Consistent format makes log parsing easier
- **Better maintainability**: Changes to message structure don't require string updates
- **Consistent error reporting**: Row numbers and context are standardized
- **Performance**: Slightly better performance than f-strings
- **Internationalization ready**: Easier to translate messages later

### Data Handling Principles

#### Missing Data: Process with Error Indicators
**Rule**: When data is missing but can be added manually later, process with clear error indicators.

**Examples of Missing Data**:
- Missing ISIN for a known symbol
- Missing country information
- Missing security details that can be manually researched

**Required Actions**:
1. **Always log an ERROR** (not just warning) with actionable guidance
2. **Include the data in output** with clear error indicators 
3. **Make problems visible** to users (Excel highlighting, warning messages)
4. **Preserve financial amounts** - never lose monetary data due to missing supplementary info
5. **Use clear identifiers** like "MISSING_ISIN_REQUIRES_ATTENTION" in output

**Code Pattern**:
```python
# ✅ GOOD - Process missing ISIN with error indicators
if not isin:
    logger.error("Missing security information for symbol %s - including dividend data but requires manual review. Please add this security to your IB account or verify the symbol.", symbol)
    isin = "MISSING_ISIN_REQUIRES_ATTENTION"
    country = "UNKNOWN_COUNTRY"
    # Continue processing with marked data
```

#### Invalid Data: Fail Fast
**Rule**: When data is invalid, corrupted, or incorrectly formatted, stop processing immediately with detailed error information.

**Examples of Invalid Data**:
- Invalid CSV file format or structure
- Invalid monetary amounts (non-numeric values)
- Invalid date formats
- Missing required columns in CSV sections
- Corrupted data that cannot be reasonably processed
- Invalid row formats that break processing logic

**Required Actions**:
1. **Stop processing immediately** - do not continue with invalid data
2. **Provide detailed error information** including row numbers and specific issues
3. **Use proper exception chaining** to preserve stack traces
4. **Include contextual information** (symbol, row number, expected format)

**Code Pattern**:
```python
# ✅ GOOD - Fail fast on invalid data
try:
    amount = Decimal(amount_str)
except ValueError as e:
    raise FileProcessingError("Row %d: Invalid monetary amount '%s' for symbol %s - expected decimal number", row_number, amount_str, symbol) from e

# ✅ GOOD - Fail fast on structural issues
if len(row) < MIN_REQUIRED_COLUMNS:
    raise FileProcessingError("Row %d: Invalid row format - expected at least %d columns, got %d: %s", row_number, MIN_REQUIRED_COLUMNS, len(row), row)
```

#### Key Principles
- **Never silently skip expected data** - either mark it clearly or fail fast
- **Preserve financial integrity** - monetary amounts should never be lost due to processing issues
- **Clear user communication** - errors must be visible and actionable
- **Distinguish missing vs invalid** - missing data can be processed with warnings, invalid data requires immediate failure

### Error Handling Patterns

#### Contextual Error Information
**Always provide sufficient context for debugging**:
```python
# ✅ GOOD - Include row number, symbol, and specific issue
raise FileProcessingError(
    "Row %d: Invalid monetary amount '%s' for symbol %s - expected decimal number", 
    row_number, amount_str, symbol
) from e

# ✅ GOOD - Include column index and expected format in context
raise FileProcessingError(
    "Row %d: Invalid Trades header format - expected columns at indices %s", 
    row_number, EXPECTED_COLUMN_INDICES
)
```

#### Exception Chaining
**Always use proper exception chaining** to preserve original context:
```python
# ✅ GOOD - Preserve original exception context
try:
    result = risky_operation()
except ValueError as e:
    raise FileProcessingError("Processing failed for %s", item) from e

# ❌ AVOID - Losing original exception information
try:
    result = risky_operation() 
except ValueError:
    raise FileProcessingError("Processing failed")
```

#### Fail Fast Decision Tree
**Use this mental model for error handling**:

1. **Is the data invalid/corrupted?** → **Fail immediately** with detailed context
2. **Is required data missing but can be provided later?** → **Process with error indicators**
3. **Is this a validation issue in business logic?** → **Fail with business rule explanation**
4. **Is this an infrastructure issue (file not found, permissions)?** → **Fail with user-actionable guidance**

#### Error Message Consistency
**Follow consistent patterns across the codebase**:
- Start with row number/location when available
- Include the problematic data in quotes
- Explain what was expected
- Provide actionable guidance if possible
- Use parameterized format for consistent formatting

**Example Implementation**:
- Use error indicators like `"MISSING_ISIN_REQUIRES_ATTENTION"` instead of skipping entries
- Highlight problematic cells in Excel with red backgrounds and warning symbols (⚠️)
- Add explanatory comments to help users understand and fix the issue
- Log clear ERROR messages that explain the problem and suggest solutions

**Rationale**: Financial data has tax and legal implications. Silent data loss can result in incorrect tax filings, regulatory compliance issues, and financial losses for users.

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
