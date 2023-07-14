# Portfolio
Simple investment portfolio tool that will track stock and provide returns and other metrics. It also
contains a web dashboard to view the data.

![workflow badge](https://github.com/jkoestner/iex/actions/workflows/main.yml/badge.svg)
[![license badge](https://img.shields.io/github/license/jkoestner/iex)](https://github.com/jkoestner/IEX/blob/main/LICENSE.md)
![coverage badge](https://img.shields.io/codecov/c/github/jkoestner/iex)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

The tool has 2 functions with 1 being a web dashboard and the other the portfolio class. The web dashboard is built with plotly dash and can be run locally or deployed to a server. The portfolio class is used to track the returns of a portfolio and can be used to track the returns of a portfolio.

Full documentation can be seen here: https://jkoestner.github.io/IEX

Data sources:
- https://iexcloud.io/
- https://pypi.org/project/yahoo-finance/

### Install packages
To install, this repository can be installed by running the following command in 
the environment of choice.

```
pip install git+https://github.com/jkoestner/IEX.git
```

If wanting to do more and develop on the code, the following command can be run to install the packages in the requirements.txt file.

```
pip install -r requirements.txt
```

### Portfolio Class

When using the portfolio class, the following code can be used to get the returns of a portfolio.

CLI coming shortly

```python
import os
os.chdir("../")
os.getcwd()
from datetime import datetime
import pandas as pd
import yfinance as yf
from iex.portfolio import portfolio, heatmap
pd.options.display.float_format = "{:,.2f}".format
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 500)
# constant variables used in program
filter_type=["Dividend"]
funds=["BLKRK"]
delisted=["AQUA", "CCIV"] 
other_fields=["broker"]
benchmarks=["IVV"]
tx_file = r"tests/files/test_transactions.xlsx"
pf = portfolio.Portfolio(
    tx_file, 
    filter_type=filter_type, 
    funds=funds, 
    delisted=delisted, 
    other_fields=other_fields,
    benchmarks=benchmarks,
    name='all'
)
```

### Web Dashboard

A demo of the app can be seen at https://koestner.fly.dev/ and was built with https://fly.io/ as the host

Pages includes:
- stocks
- sectors
- ideas
- macros
- trackers
- crypto

It also can be run locally by going to the project root folder and running below.
There are a number of environment variables listed in constants to be able to run locally. 

```python
python app.py
```
## Jupyter Lab Usage

To have conda environments work with Jupyter Notebooks a kernel needs to be defined. This can be done defining a kernel, shown below when
in the conda environment.

```
python -m ipykernel install --user --name=iex
```

## Logging

If wanting to get more detail in output of messages the logging can increased
```python
import logging
logger = logging.getLogger('iex.portfolio.portfolio')
logger.setLevel(logging.WARNING)  # default: only print WARNINGS and above
logger.setLevel(logging.CRITICAL)  # disable printing
logger.setLevel(logging.DEBUG)  # verbose: print errors & debug info
```

## Coverage

To see the test coverage the following command is run in the root directory. This is also documented in the `.coveragerc` file.
```
pytest --cov=iex --cov-report=html
```