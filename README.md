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

### **Source Files Configuration**
- **Input Data**: Add your Interactive Brokers CSV export to the `/resources/source` folder. See `/resources/shares_example.csv` for an example of the file format.
  - *Note*: Future updates will support additional data sources (crypto exchanges, DeFi platforms, etc.)
- **Currency Rates**: Update `config.ini` with all required currency exchange pairs.
  - E.g. you can use the exchange rates from the last day of the year from your national central bank or financial institution.

## Installation & Usage

### **Using Poetry (Recommended)**

```bash
# Install dependencies
cd shares-reporting
poetry install

# Run the application
poetry run shares-reporting
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