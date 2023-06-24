# IEX
IEX cloud finance

![workflow badge](https://github.com/jkoestner/iex/actions/workflows/main.yml/badge.svg)

## Overview

The app can be seen at https://koestner.fly.dev/ and was built with https://fly.io/ as the host

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

The code also contains a portfolio class to help build the returns from stock transactions.

Full documentation can be seen here: https://jkoestner.github.io/IEX

Data sources:
- https://iexcloud.io/
- https://www.alphavantage.co
- https://pypi.org/project/yahoo-finance/

## Install packages
To install packages, this repository can be installed by cloning the repository to a desktop location. Then opening a command terminal and changing directory
to the root of the project and running the following command in the environment of choice.

```
pip install -r requirements.txt
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