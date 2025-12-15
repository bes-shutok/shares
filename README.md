# Investment Reporting Tool

## Overview

The investment reporting tool is designed to provide a simple and efficient way to generate capital gains data for tax reporting purposes. The tool can be used for reporting in various countries with similar requirements of grouping bought/sold investments.

**Current Capabilities:**
- ✅ **Share Trading**: Processes Interactive Brokers CSV reports for stock trading
- ✅ **Capital Gains Calculation**: FIFO-based matching of buy/sell transactions within daily buckets
- ✅ **Capital Gains Reporting**: Generates Excel reports with capital gains data for tax authority submission
- ✅ **Dividend Income Reporting**: Processes dividend data and generates detailed dividend income reports
- ✅ **Multi-Currency Support**: Handles multiple currencies with manual exchange rate configuration

**Future Vision:**
- 🚀 **Additional Investment Types**: Support for crypto currency trading, DeFi protocols, staking rewards, and other investment vehicles
- 🚀 **Multiple Data Sources**: Integration with crypto exchanges (Binance, Coinbase, Kraken), DeFi platforms, and other financial APIs
- 🚀 **Advanced Matching**: Sophisticated algorithms for different investment types and tax optimization strategies
- 🚀 **Automated Exchange Rates**: Real-time currency conversion from multiple financial data providers

## Prerequisites

## Development Environment

### Virtual Environment Setup

To ensure your editor's language server (e.g., ZED) can properly detect the project dependencies, configure Poetry to create the virtual environment in the project directory:

```bash
# Install dependencies
uv sync --extra dev
```

This will create a `.venv` folder in your project root that editors can detect automatically.



### Python Requirements

- **Python 3.14+ required** (Modern Python features, `datetime.UTC` alias)
- **UV for dependency management** (recommended approach)
- **Professional package structure** with `src/` layout
- **Clean Architecture** with Domain-Driven Design
- **Type hints extensively used** throughout codebase
- **pytest framework** with comprehensive unit and integration tests
- **Modern tooling**: Ruff linter/formatter, coverage reporting, professional packaging

### **Source Files Configuration**
- **Input Data**: Add your Interactive Brokers CSV export to the `/resources/source` folder. See `/resources/shares_example.csv` for an example of the file format.
  - *Note*: Future updates will support additional data sources (crypto exchanges, DeFi platforms, etc.)
- **Currency Rates**: Update `config.ini` with all required currency exchange pairs.
  - E.g. you can use the exchange rates from the last day of the year from your national central bank or financial institution.
  - The config file also includes security validation settings (file size limits, allowed extensions, etc.)
- **Missing Buy History**: If securities are sold without corresponding buy transactions in the IB export, the tool automatically creates placeholder buy transactions (date: 1000-01-01, price: 0) to allow capital gains calculation. These entries are highlighted in red in the Excel report for manual review.

## Installation & Usage

### **Using UV (Recommended)**

```bash
# Install dependencies
cd shares-reporting
uv sync --extra dev

# Run the application
uv run shares-reporting
```

### Testing

```bash
# Using UV (recommended)
uvx pytest                       # Run all tests
uvx pytest -k <keyword>          # Run tests matching keyword
uvx pytest -vvl                 # Verbose output with all variables
uvx pytest --cov=.              # Run with coverage
```

### Code Quality and Linting

```bash
# Run Ruff linter (checks code quality)
uvx ruff check .                    # Check all files
uvx ruff check . --fix              # Auto-fix issues
uvx ruff check . --statistics       # Show issue statistics
uvx ruff check src/ tests/          # Check specific directories

# Run Ruff formatter (formats code)
uvx ruff format .                   # Format all files
uvx ruff format --check .           # Check if formatting is needed

# Combined workflow
uvx ruff check . --fix && uvx ruff format .  # Fix and format
```



### **Report Features**
The tool generates comprehensive Excel reports with:
- **Capital Gains Section**: Detailed buy/sell transaction matching with FIFO methodology
- **Dividend Income Section**: Complete dividend reporting with tax information and original currency amounts
- **Professional Formatting**: Currency display with 2 decimal places and proper Excel formulas
- **Multi-Currency Support**: Automatic currency conversion with exchange rate tables
- **ISIN Integration**: Automatic country of source detection from financial instrument data

## Roadmap & Future Development

### **Planned Investment Type Support**
- **Crypto Currency Trading**: Buy/sell transactions across different exchanges
- **Earnings**: Various forms of investment earnings and rewards
- **Fixed Income**: Bond interest payments and maturity tracking

### **Planned Data Source Integration**
- **Crypto Exchanges**: Direct API integration with major cryptocurrency exchanges
- **DeFi Platforms**: Support for decentralized finance protocols and platforms
- **Additional Brokers**: Support for other traditional broker CSV formats

### **Potential Future Enhancements (Low Priority)**
- **Trade Matching Strategies**: Support for LIFO (Last In, First Out) and HIFO (Highest In, First Out) strategies for users in jurisdictions with different tax regulations

## Feedback
Please create issues to provide feedback!