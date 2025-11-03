# Investment Reporting Tool

## Overview

The investment reporting tool is designed to provide a simple and efficient way to generate preliminary data for tax reporting in Portugal. The same tool can be used for reporting in other countries with similar requirements of grouping bought/sold investments.

**Current Capabilities:**
- ✅ **Share Trading**: Processes Interactive Brokers CSV reports for stock trading
- ✅ **Capital Gains Calculation**: FIFO-based matching of buy/sell transactions within daily buckets
- ✅ **Tax Reporting**: Generates Excel reports with currency conversion for Portuguese tax requirements
- ✅ **Multi-Currency Support**: Handles multiple currencies with manual exchange rate configuration

**Future Vision:**
- 🚀 **Multiple Investment Types**: Support for dividends, crypto currency trading, DeFi protocols, staking rewards, and other investment vehicles
- 🚀 **Multiple Data Sources**: Integration with crypto exchanges (Binance, Coinbase, Kraken), DeFi platforms, and other financial APIs
- 🚀 **Advanced Matching**: Sophisticated algorithms for different investment types and tax optimization strategies
- 🚀 **Automated Exchange Rates**: Real-time currency conversion from multiple financial data providers

## Architecture & Design Philosophy

This project follows **Clean Architecture** principles with **Domain-Driven Design** and professional Python package structure. The architecture is designed to be extensible for future investment types and data sources.

### **Layered Architecture**
- **Domain Layer** (`src/shares_reporting/domain/`): Core business entities and rules (investment-agnostic)
- **Application Layer** (`src/shares_reporting/application/`): Business logic and orchestration
- **Infrastructure Layer** (`src/shares_reporting/infrastructure/`): External concerns (config, APIs, data sources)
- **Presentation Layer** (`src/shares_reporting/main.py`): Application entry point

### **Extensibility Design**
The clean architecture ensures that adding new investment types and data sources requires minimal changes:
- **New Investment Types**: Add domain entities and application services without affecting existing code
- **New Data Sources**: Implement new extraction adapters in the infrastructure layer
- **New Tax Rules**: Extend transformation logic with country-specific calculations

### **Professional Package Structure**
```
src/shares_reporting/
├── domain/                    # Domain Layer (investment-agnostic)
│   ├── value_objects.py       # TradeDate, Currency, Company, TradeType
│   ├── entities.py            # TradeAction, TradeCycle, CapitalGainLine
│   ├── accumulators.py        # CapitalGainLineAccumulator, TradePartsWithinDay
│   └── collections.py         # Type aliases and collections
├── application/               # Application Layer
│   ├── extraction.py          # Data parsing (currently CSV, extensible to APIs)
│   ├── transformation.py      # Investment calculations and matching
│   └── persisting.py          # Report generation (Excel, CSV, future formats)
├── infrastructure/             # Infrastructure Layer
│   └── config.py              # Configuration and external service management
└── main.py                    # Application entry point
```

The initial implementation has been **refactored** from a flat structure to a professional modular architecture while maintaining the same business functionality and backward compatibility. This architecture prepares the codebase for future expansion into multiple investment types and data sources.

# Table of Contents
- [Prerequisites](#prerequisites)
- [Modules](#modules)
- [Usage](#usage)
- [Roadmap & Future Development](#roadmap--future-development)
- [Debugging](#debugging)
- [Additional Practice](#additional-practice)
- [Feedback](#feedback) - Please create issues to provide feedback!


## Prerequisites
### **Update source files**
  - **Current**: Add Interactive Brokers CSV file to `/resources/source` folder. See `/resources/shares_example.csv` for an example of the file format.
  - **Future**: Additional data sources will be supported (crypto exchanges, DeFi platforms, etc.)
  - Update config.ini with all required currency exchange pairs.
    E.g. for Portugal it can be the exchange rates from the last day of the year (https://www.bportugal.pt/en/page/currency-converter) 

### Setting Up Development Environment

#### **Option 1: Using Poetry (Recommended)**

Poetry provides modern dependency management and virtual environment handling.

**Step 1: Install Poetry**
```bash
# For macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# For Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python3 -

# Or via pip (less recommended)
pip install poetry
```

**Step 2: Install Dependencies**
```bash
cd shares-reporting
poetry install
```

**Step 3: Activate Virtual Environment**
```bash
poetry shell
```

**Step 4: Run the Application**
```bash
# Using Poetry (recommended)
poetry run shares-reporting

# Or directly
poetry run python ./src/shares_reporting/main.py
```


## Usage

### **Using Poetry (Recommended)**
```bash
cd shares-reporting
poetry install
poetry run shares-reporting
```


### **Configuration**
- Ensure `config.ini` has all required currency exchange pairs
- Update source files in `/resources/source` folder
- For Portugal, use exchange rates from Banco de Portugal (last day of the year)

## Architecture & Modules

### **Domain Layer** (`src/shares_reporting/domain/`)
Core business entities and rules that are independent of external concerns:
- **`value_objects.py`** - Value objects: TradeDate, Currency, Company, TradeType (extensible for new investment types)
- **`entities.py`** - Core entities: TradeAction, TradeCycle, CapitalGainLine (foundation for other investment vehicles)
- **`accumulators.py`** - Business accumulators: CapitalGainLineAccumulator, TradePartsWithinDay
- **`collections.py`** - Type aliases and collection utilities

### **Application Layer** (`src/shares_reporting/application/`)
Business logic services and orchestration components:
- **`extraction.py`** - Data parsing utilities (currently CSV, extensible to APIs and other formats)
- **`transformation.py`** - Investment calculations and matching algorithms (extensible for different investment types)
- **`persisting.py`** - Report generation with formulas (Excel, CSV, future formats)

### **Infrastructure Layer** (`src/shares_reporting/infrastructure/`)
External concerns and technical details:
- **`config.py`** - Configuration management and currency exchange rates (future: API clients, data adapters)

### **Presentation Layer**
- **`main.py`** - Application entry point and main orchestration (future: web interface, API endpoints)


## Testing

The project follows **comprehensive testing best practices** with a well-organized test structure:

### **Test Structure**
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

### **Running Tests**

#### **Using Poetry (Recommended)**
```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src --cov-report=html

# Run tests by layer
poetry run pytest tests/domain/           # Domain layer tests
poetry run pytest tests/application/        # Application layer tests
poetry run pytest tests/infrastructure/     # Infrastructure tests

# Run tests matching a keyword
poetry run pytest -k <test_keyword>

# Run tests with verbose output
poetry run pytest -vvl

# Run specific test file
poetry run pytest tests/domain/test_value_objects.py

# Run only unit tests (exclude integration)
poetry run pytest tests/domain/ tests/application/ tests/infrastructure/
```

### **Test Coverage**
```bash
# Generate coverage report
poetry run pytest --cov=src --cov-report=html

# Check coverage statistics
poetry run pytest --cov=src --cov-report=term-missing
```

### **Debugging Tests**
- Add `breakpoint()` or `import pdb; pdb.set_trace()` to debug
- Use `pytest -vvl` for maximum verbosity
- Use `pytest -s` to see print statements during tests
- Use `pytest --tb=short` for concise error output


## Roadmap & Future Development

### **Planned Investment Type Support**
- **Dividends**: Dividend income tracking and tax reporting
- **Crypto Currency Trading**: Buy/sell transactions across different exchanges
- **Earnings**: Various forms of investment earnings and rewards

### **Planned Data Source Integration**
- **Crypto Exchanges**: Direct API integration with major cryptocurrency exchanges
- **DeFi Platforms**: Support for decentralized finance protocols and platforms
- **Additional Brokers**: Support for other traditional broker CSV formats

### **Development Focus**
The clean architecture design ensures that adding new investment types and data sources can be done with minimal impact on existing functionality, allowing for gradual expansion of capabilities.

---

## Debugging

If you'd like to debug a piece of code, you can add either of the following built-in functions
to a section of the code to enter into the pdb debugger while running tests:
- `breakpoint()` (Python 3.7+)
- `import pdb; pdb.set_trace()` (compatible with older versions)