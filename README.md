# Portfolio
Simple investment portfolio tool that will track stock and provide returns and other metrics. It also
contains a web dashboard to view the data.

![workflow badge](https://github.com/jkoestner/iex/actions/workflows/main.yml/badge.svg)
[![license badge](https://img.shields.io/github/license/jkoestner/iex)](https://github.com/jkoestner/IEX/blob/main/LICENSE.md)
[![codecov](https://codecov.io/gh/jkoestner/IEX/branch/main/graph/badge.svg?token=K4RS9LX4UG)](https://codecov.io/gh/jkoestner/IEX)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

The tool has 2 functions with 1 being a web dashboard and the other the portfolio class. The web dashboard is built with plotly dash and can be run locally or deployed to a server. The portfolio class is used to track the returns of a portfolio.

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

```python
from iex import constants, portfolio
config_path = constants.CONFIG_PATH / "portfolio.ini"
pf = portfolio.Portfolio(
    config_path=config_path, 
    portfolio='tracker'
)
pf.get_performance()
```

### Web Dashboard

A demo of the app can be seen at https://koestner.fly.dev/.


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