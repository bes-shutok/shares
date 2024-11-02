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
**Add source file**
  - Add source file to /resources/source folder. See /resources/shares_example.csv for an example of the file format.

**Install Docker**
  - The tests have been packaged to run with all dependencies
    installed within a Docker container. Due to the use of f-strings,
    this must be run with python 3.6+. The Docker image is based on python 3.7


## Modules
### reporting
Main script which processes data and create resulting reports

### domain
Domain data classes

### extraction
Utils for extracting data from source files

### transofrmation
Utils used to massage the shares data

### persisting
Utils that persist the data


## Tests
**To run tests rebuild image and run terminal on the docker container**

  ```bash

  $ docker compose build
  $ docker compose run test sh
  ```


**This will open the docker shell and you can run one of the following commands:**


  *Run the entire test suite*
    
  ``` bash
  $ pytest 
  ```

  *Run the tests for a certain file matching a keyword*
    
  ``` bash
  $ pytest -k <test_file_name>
  ```

  *Run tests while printing all variables and verbose output*

  ``` bash
  $ pytest -vvl
  ```

**To exit the shell**
  ```bash
  $ exit
  ```


## Debugging

1. If you page up `(ctrl + fn)` within the debug output when running `pytest -vvl` or
when encountering test errors, your cursor may stick and be unable to continue 
writing in the docker shell. You can get past this by typing `q` to return to
entry mode in the docker container.


1. If you'd like to debug a piece of code, you can add either of the following built-in functions
   to a section of the code to enter into the pdb debugger while running pytest. 
   * `breakpoint()` (python 3)
   * `import pdb; pdb.set_trace()` (python 2)