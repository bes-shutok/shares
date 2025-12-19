# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shares reporting tool is a financial application that processes Interactive Brokers CSV reports to generate tax reporting data for capital gains and dividend income calculations. It matches buy/sell transactions within the same day to calculate capital gains, processes dividend payments with tax information, and generates comprehensive Excel reports with currency conversion.

## Quick Start

```bash
# Using UV (recommended)
uv run shares-reporting

# Direct execution (alternative)
uv run python ./src/shares_reporting/main.py

# Ensure config.ini has all required currency exchange pairs
# Update source files in /resources/source folder
```

## Environment and Dependency Management

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

### Development Commands Reference

#### Setup and Dependency Management
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

#### Development Workflow
```bash
# Quick development cycle
uvx pytest                     # Run tests (fast)
uvx ruff check . --fix && uvx ruff format .  # Lint and format (fast)
uv run shares-reporting       # Run the application
```

#### Quality Assurance
```bash
# Run all tests
uvx pytest

# Run with coverage
uvx pytest --cov=src --cov-report=html

# Linting and formatting
uvx ruff check .
uvx ruff format .
uv run basedpyright src/ tests/  # Type checking
```

### Common Mistakes to Avoid
- `uvx shares-reporting` - ❌ Won't work (project is not published to PyPI)
- `uvx run shares-reporting` - ❌ Installs 'run' package, not what you want
- `uv run shares-reporting` - ✅ Correct way to run the local application

**Key point**: This project uses a local entry point defined in `pyproject.toml`, not a published PyPI package.

## Architecture

The project follows **professional layered architecture** with **Domain-Driven Design** principles:

### Layered Architecture
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

#### Data Processing Flow
The system processes data through a sophisticated tax-compliant pipeline:
1. **Extraction**: `parse_ib_export_all()` parses Interactive Brokers CSV files into domain objects (trades + dividends + security info)
2. **Transformation**: `calculate_fifo_gains()` implements the core capital gains algorithm
3. **Persistence**: `generate_tax_report()` creates Excel reports + `export_rollover_file()` for inventory rollover

#### CSV Extraction Architecture

The `extraction` package uses a **State Machine** pattern to parse complex Interactive Brokers CSV files:

**Components:**
- **`IBCsvStateMachine`**: Orchestrates the parsing process, transitioning between file sections. Supports optional Financial Instrument section validation for different file types.
- **Contexts** (`contexts.py`): Specialized handlers for each CSV section:
  - `FinancialInstrumentContext`: Extracts security info (ISIN, Country).
  - `TradesContext`: Parses trade executions. Trades section is always required for real CSV files.
  - `DividendsContext`: Extracts dividend records.
  - `WithholdingTaxContext`: Parses tax records.
- **Models** (`models.py`): Data structures for raw extracted data (`IBCsvData`, `IBCsvSection`).

**Flow:**
1. `IBCsvStateMachine` reads the CSV row by row.
2. Detects section headers (e.g., "Financial Instrument Information", "Trades").
3. Delegates row processing to the active `BaseSectionContext` subclass.
4. Aggregates results into `IBCsvData` for downstream processing.

**Configuration:**
- **Export files**: Require both Trades and Financial Instrument sections (default behavior)
- **Leftover files**: Require Trades section but Financial Instrument section is optional (for processing legacy trade data without security info)

#### FIFO Algorithm Deep Dive

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

### Domain Model Details

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

### Automatic Leftover Integration

The system automatically integrates data from previous tax cycles:

**Feature Overview:**
- **Automatic Detection**: If `shares-leftover.csv` exists in the same directory as an export file, it's automatically integrated
- **Data Enrichment**: Leftover trades are enriched with security information (ISIN, country) from the current export file
- **FIFO Preservation**: Leftover trades (older) are placed before current year trades to maintain proper chronological ordering
- **Backward Compatibility**: If no leftover file exists, processes normally without any changes

**Integration Process:**
1. **Security Info Extraction**: Extracts security mapping from current export file
2. **Trade Combination**: Merges leftover trades + current export trades
3. **Processing**: Runs unified trade processing with complete security context
4. **Reporting**: Generates comprehensive capital gains calculations across all time periods

**File Formats:**
- **Export file** (`ib_export.csv`): Contains complete data with all sections
- **Leftover file** (`shares-leftover.csv`): Contains unmatched trades from previous cycle with extended columns (Basis, Realized P/L)
- **Output rollover**: Updated each year with new unmatched trades for next cycle

## Testing Strategy

### Comprehensive Test Suite Overview
The project follows **professional testing best practices** with a **3-tier test architecture** and comprehensive coverage:

### Test Structure
```
tests/
├── unit/          # 156 unit tests - Fast component tests
│   ├── domain/    # Domain layer unit tests
│   ├── infrastructure/  # Infrastructure layer unit tests
│   └── application/ # Application layer unit tests
├── integration/   # 48 integration tests - Component interaction tests
└── end_to_end/    # 6 e2e tests - Full workflow tests
```

### Testing Commands
```bash
# Run all tests
uvx pytest

# Run tests by tier using markers
uvx pytest -m unit         # Unit tests only (fast)
uvx pytest -m integration  # Integration tests only
uvx pytest -m e2e          # End-to-end tests only

# Run tests by directory
uvx pytest tests/unit/             # All unit tests
uvx pytest tests/unit/domain/      # Domain layer tests
uvx pytest tests/unit/infrastructure/  # Infrastructure tests
uvx pytest tests/unit/application/     # Application layer tests
uvx pytest tests/integration/      # Integration tests
uvx pytest tests/end_to_end/       # End-to-end tests

# Run with coverage
uvx pytest --cov=src --cov-report=html

# Run specific test patterns
uvx pytest -k "test_specific"     # Run tests matching pattern
uvx pytest tests/unit/domain/test_value_objects.py  # Specific test file

# Development workflow
uvx pytest -m unit -x            # Run unit tests, stop on first failure
uvx pytest -m unit --tb=short    # Short traceback for faster debugging
```

### Testing Guidelines

#### Core Testing Principles
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Edge Cases**: Comprehensive error handling and boundary conditions
- **Test Coverage**: High coverage of business logic and validation
- **Descriptive Naming**: Clear test names that document behavior
- **Debugging**: Use `breakpoint()` or `import pdb; pdb.set_trace()`

#### Pytest Best Practices

**Critical Rule**: Do not import pytest fixtures - they are injected automatically by name.

**Available Fixtures Without Import**:
- `tmp_path` - Filesystem operations (pathlib.Path)
- `capsys` - Capture stdout/stderr
- `caplog` - Capture logging output
- `monkeypatch` - Patch environment/attributes
- `request` - Test context and metadata

**Example Usage**:
```python
# ✅ GOOD - Use directly without imports
def test_something(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

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

#### Test Value Assessment
Ask these questions for every test:
1. **Does it test meaningful business logic** that could break in production?
2. **Does it test real edge cases** from actual data/usage?
3. **Is it testing something not already covered** by other tests?
4. **Would a failure provide actionable information** for debugging?

**High-Value Test Patterns to Include**:
- Complex IB CSV description formats
- Missing data scenarios with error indicators  
- Tax calculation and matching logic
- Integration flows between components
- Error handling and validation paths
- Performance with realistic datasets
- Real edge cases from actual exports

**Low-Value Test Patterns to Avoid**:
- Testing zero amounts (if positives work, zeros work too)
- Testing basic string parsing that should work anyway
- Testing simple symbol matching (AAPL/MSFT basics)
- Testing very small decimal amounts without business meaning
- Testing trivial cases that would be caught by other tests

## Development Best Practices

### Incremental Development with Testing
**Test-driven approach for complex changes**:
1. **Write failing tests first** to understand expected behavior
2. **Implement changes** with comprehensive test coverage
3. **Run the full test suite** to ensure no regressions
4. **Review and clean up** low-value tests after functionality works

### API Design Consistency
**Maintain consistent patterns across similar functions**:
```python
# ✅ GOOD - Consistent parameter patterns across context methods
def process_header(self, row: list[str], row_number: int) -> None:
def process_data_row(self, row: list[str], row_number: int) -> None:

# ✅ GOOD - Consistent error message patterns
raise FileProcessingError("Row %d: Invalid %s format", row_number, section_name)
```

### Code Review Checklist
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

### Documentation Maintenance
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

### Complexity Management
- Functions with high complexity (`PLR0912`, `PLR0915`) should be refactored when possible
- If refactoring is too risky, use explicit `# noqa: PLR0912, PLR0915` with a comment explaining why
- Avoid deeply nested logic; extract helper functions

## Data Handling Principles

### Missing Data: Process with Error Indicators
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

### Invalid Data: Fail Fast
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

### Key Principles
- **Never silently skip expected data** - either mark it clearly or fail fast
- **Preserve financial integrity** - monetary amounts should never be lost due to processing issues
- **Clear user communication** - errors must be visible and actionable
- **Distinguish missing vs invalid** - missing data can be processed with warnings, invalid data requires immediate failure

## Error Handling Patterns

### Contextual Error Information
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

### Exception Chaining
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

### Preferred Logging and Error Message Format

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
│   ├── unit/               # Unit tests (156 tests)
│   │   ├── domain/         # Domain layer unit tests
│   │   ├── infrastructure/ # Infrastructure layer unit tests
│   │   └── application/    # Application layer unit tests
│   ├── integration/        # Integration tests (48 tests)
│   ├── end_to_end/         # End-to-end tests (6 tests)
│   └── conftest.py         # Pytest configuration and fixtures
├── resources/              # Data directories
│   ├── source/             # Input CSV files
│   └── result/             # Generated reports
├── pyproject.toml          # Poetry configuration and dependencies
├── config.ini              # Application configuration
├── README.md               # Project documentation
└── CLAUDE.md              # This file - Claude Code guidance
```

## Lessons Learned

### Common Issues and Prevention Strategies

Based on recurring patterns in code fixes, here are rules to prevent similar mistakes:

#### 1. Code Quality and Duplication
- **Issue**: Duplicate test methods or functions with identical names
- **Prevention**: Always check for duplicates before adding new code
- **Command**: `grep -n "def method_name" . -r` to search for existing methods

#### 2. Type Safety and Annotations
- **Missing decorators**: Always add `@override` to methods overriding base class methods
- **Class attributes**: Annotate all class attributes with types unless class is marked `@final`
- **Method parameters**: Prefix unused parameters with underscore (`_param`) or use `_` for completely unused
- **Pattern**:
  ```python
  class MyClass:
      attr1: Type1  # Required if class not @final
      
      @override
      def method_name(self, _param: UnusedType):  # Unused parameter
          pass
  ```

#### 3. String and Code Formatting
- **Implicit concatenation**: Keep f-strings on single lines or use explicit concatenation
- **Line length**: Break long lines appropriately, especially for error messages
- **Example**:
  ```python
  # Good
  error_message = (
      f"Error in row {row_number}: "
      f"Expected format X, got Y"
  )
  
  # Avoid
  error_message = f"Error in row {row_number}: " f"Expected format X, got Y"
  ```

#### 4. Function and Method Design
- **Parameter naming**: Use parameter names that match the interface you're implementing
- **Example**: `lambda optionstr: optionstr` not `lambda option: option` for ConfigParser
- **Required vs Optional**: Use required parameters for essential data, optional only with meaningful defaults

#### 5. Dependencies and Imports
- **Missing packages**: Check imports against dependencies and install missing packages
- **Import organization**: Import from correct modules, check `__all__` exports for public API
- **Private imports**: Avoid importing `_private` functions in tests unless necessary
- **Prevention**: Run tests early to catch missing imports

#### 6. Testing Best Practices
- **Test structure**: Use 3-tier structure
  - Unit tests (`tests/unit/`): Fast, isolated tests, can use internal functions
  - Integration tests (`tests/integration/`): Component interactions, use only public APIs
  - E2E tests (`tests/end_to_end/`): Full workflows, use only public APIs
- **Pytest markers**: Use `@pytest.mark.unit`, `pytest.mark.integration`, `pytest.mark.e2e`
- **Test organization**: Structure tests in separate directories with clear purposes

#### 7. Refactoring and Maintenance
- **Incremental changes**: Make small, incremental changes
- **Test frequently**: Run tests after each change, fix issues immediately
- **Version control**: Use version control to track progress
- **Script cleanup**: Remove temporary scripts after use
- **Pattern**: 
  1. Make change
  2. Run tests
  3. Fix if broken
  4. Repeat

#### 8. Error Handling and Logging
- **Contextual errors**: Always include sufficient context (row numbers, problematic data)
- **Exception chaining**: Use proper exception chaining to preserve original context
- **Logging format**: Use parameterized format for logging, f-strings for exceptions
- **Pattern**:
  ```python
  # Logging
  logger.error("Row %d: Invalid amount %s for symbol %s", row_number, amount, symbol)
  
  # Exceptions
  raise ValueError(f"Invalid value: {value}") from original_error
  ```

#### 9. API Design for Production vs Testing
- **Don't add features just for tests**: API design should reflect real-world usage, not test requirements
- **Tests should adapt to production code**: Update tests to match production patterns rather than modifying production to support tests
- **Example**: When tests require optional parameters, consider whether the test data structure can be adjusted instead
- **Refactoring approach**: If tests need special handling, first try to make tests reflect real usage before adding complexity to production code

#### 10. Test Path and Fixture Management
- **Avoid fragile path construction**: Never use `Path(__file__).parent.parent` in tests - these break when test files move
- **Use pytest fixtures**: Always use `tmp_path`, `tmp_path_factory`, or other provided fixtures for test file operations
- **Test data isolation**: Keep test data separate from production data and use proper fixture setup
- **Pattern**:
  ```python
  # ✅ GOOD - Use pytest fixtures
  @pytest.fixture
  def test_file(tmp_path: Path) -> Path:
      test_file = tmp_path / "test.csv"
      test_file.write_text("test,data")
      return test_file
  
  # ❌ AVOID - Fragile path construction
  def test_something():
      test_file = Path(__file__).parent.parent / "resources" / "test.csv"
  ```

#### 11. Simplify Unnecessary Complexity
- **Remove unused parameters**: If a parameter is always the same value (e.g., always `True`), remove it entirely
- **YAGNI principle**: You Aren't Gonna Need It - don't add features "just in case"
- **Constant parameters**: Parameters with constant values add unnecessary complexity and make the API harder to understand
- **Example**: `require_trades_section=True` parameter that's always `True` should be removed and the behavior hardcoded

#### 12. Test Real Behavior, Not Implementation Details
- **Test functionality, not return values**: Verify that the feature actually works as expected, not just that it returns certain values
- **Use meaningful test data**: Test with realistic data that represents actual usage scenarios
- **Integration verification**: Ensure that components work together correctly, not just in isolation
- **Example**: When testing leftover data integration, verify that the integrated data actually contains more trades than without integration

### Pre-Commit Checklist

Enhanced checklist based on recent fixes:

1. **Tests**: `uv run pytest -x` (stop on first failure)
2. **Linting**: `uv run ruff check . --fix` (auto-fix where possible)
3. **Type checking**: `uv run basedpyright src/ tests/`
4. **Line length check**: `uv run ruff check . --select=E501`
5. **Import verification**: Ensure all imports have corresponding dependencies
6. **Path construction check**: `grep -r "Path(__file__)" tests/` - ensure no fragile test paths
7. **Parameter usage check**: Review new parameters - are they always constant?
8. **Test behavior verification**: Do tests verify actual functionality vs just return values?
9. **Clean up**: Remove any temporary files or scripts
10. **Documentation**: Update relevant documentation if API changes were made

### Quality Assurance Commands

```bash
# Check for specific issue types
uv run ruff check . --select=E501  # Line length
uv run ruff check . --select=F401  # Unused imports
uv run ruff check . --select=PL  # Pylint rules

# Check for fragile path construction in tests
grep -r "Path(__file__)" tests/ || echo "✅ No fragile test paths found"

# Check for parameters that might always be constant
grep -r "= True" src/ --include="*.py" | grep -v "def " | head -10

# Run tests by marker during development
uv run pytest -m unit       # Fast feedback during development
uv run pytest -m integration  # Before committing
uv run pytest -m e2e         # Before release

# Check for duplicate test methods
grep -n "def test_" tests/ | cut -d: -f3 | sort | uniq -d
```