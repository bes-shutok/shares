# Shares Reporting Tool

## Overview

The shares reporting tool is designed to provide a simple and efficient way to generate preliminary data for tax reporting in Portugal. The same tool can be used for reporting in other countries with similar requirements of grouping bought/sold shares.
Currently, the tool joins shares bought/sold within a day.

## Initial Implementation

The initial implementation of the shares reporting tool uses standard yearly reports generated from my own Interactive Brokers' account. The report is generated in the form of an Excel file, where each share is accumulated in one line with the same amount of shares bought and sold.

# Table of Contents
- [Prerequisites](#prerequisites)
- [Modules](#modules)
- [Usage](#usage)
- [Debugging](#debugging)
- [Additional Practice](#additional-practice)
- [Feedback](#feedback) - Please create issues to provide feedback!


## Prerequisites
### **Update source files**
  - Add source file to /resources/source folder. See /resources/shares_example.csv for an example of the file format.
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
python ./reporting.py
# Or using Poetry
poetry run python ./reporting.py
```


## Usage

### **Using Poetry (Recommended)**
```bash
cd shares-reporting
poetry install
poetry run python ./reporting.py
```


### **Configuration**
- Ensure `config.ini` has all required currency exchange pairs
- Update source files in `/resources/source` folder
- For Portugal, use exchange rates from Banco de Portugal (last day of the year)

## Modules
### reporting
Main script which processes data and create resulting reports

### domain
Domain data classes

### extraction
Utils for extracting data from source files

### transformation
Utils used to massage the shares data

### persisting
Utils that persist the data


## Tests

### **Using Poetry (Recommended)**
```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=. --cov-report=html

# Run tests matching a keyword
poetry run pytest -k <test_keyword>

# Run tests with verbose output
poetry run pytest -vvl

# Run specific test file
poetry run pytest tests/test_reporting.py
```


### **Test Coverage**
```bash
# Generate coverage report
poetry run pytest --cov=. --cov-report=html
```

### **Debugging Tests**
- Add `breakpoint()` or `import pdb; pdb.set_trace()` to debug
- Use `pytest -vvl` for maximum verbosity
- Use `pytest -s` to see print statements during tests


## Debugging

If you'd like to debug a piece of code, you can add either of the following built-in functions
to a section of the code to enter into the pdb debugger while running tests:
- `breakpoint()` (Python 3.7+)
- `import pdb; pdb.set_trace()` (compatible with older versions)