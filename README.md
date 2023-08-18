<div align="center">
  <img src="https://user-images.githubusercontent.com/50647092/260895211-7e9a8e6e-9f85-48ed-bb61-49ff2ff805b6.png"><br>
</div>

# Portfolio
Simple investment portfolio tool that will track stock and provide returns and other metrics. It also contains a web dashboard to view the data.

![workflow badge](https://github.com/jkoestner/folioflex/actions/workflows/main.yml/badge.svg)
[![license badge](https://img.shields.io/github/license/jkoestner/folioflex)](https://github.com/jkoestner/folioflex/blob/main/LICENSE.md)
[![codecov](https://codecov.io/gh/jkoestner/folioflex/branch/main/graph/badge.svg?token=K4RS9LX4UG)](https://codecov.io/gh/jkoestner/folioflex)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
  - [Install packages](#install-packages)
- [Usage](#usage)
  - [CLI](#cli)
  - [Python](#python)
  - [Web Dashboard](#web-dashboard)
- [Other Tools](#other-tools)

## Overview

**🚀 Welcome to FolioFlex! 🚀**

**📖 Description:**

- FolioFlex is your go-to toolkit for portfolio management and market analysis! Dive into the world of stocks, bonds, and more with our user-friendly tools. 📈📊

**🔧 Features:**

- Dashboard Helper: Get a quick overview of your portfolio with our dashboard. 🖥️
- Market Screener: Filter and find trending stocks. 🔍
- Portfolio Management: Organize and track, your investments. 💼
- Config Helper: Customize your experience with easy configurations. ⚙️

**📚 Documentation:**

- Installation Guide: Get started with FolioFlex in no time! 🛠️
- Usage Guide: Learn how to make the most out of FolioFlex. 🤓

**🔬 Examples:**

- Portfolio Example: Explore a sample portfolio and see FolioFlex in action! 📔

**🎥 See It In Action:**

- FolioFlex Demo: Visit a dashboard (https://koestner.fly.dev/) of FolioFlex and witness the magic! 🌟

**🤝 Contribute:**
- Love FolioFlex? Feel free to contribute and make it even better! Every bit of help is appreciated. ❤️

Full documentation can be seen here: https://jkoestner.github.io/folioflex

Data sources:
- https://pypi.org/project/yahoo-finance/
- https://fred.stlouisfed.org/docs/api/fred/ (need an API key)
- https://finviz.com/api

Inspiration:
- https://openbb.co/

## Installation

### Install packages
To install, this repository can be installed by running the following command in 
the environment of choice.

```
pip install git+https://github.com/jkoestner/folioflex.git
```

If wanting to do more and develop on the code, the following command can be run to install the packages in the requirements.txt file.

```
pip install -r requirements.txt
```
## Usage

### CLI

CLI can be used for easier commands of python scripts for both portfolio or manager. An example of a CLI command is shown below.

```commandline
ffx manager --email "your_name@outlook.com" --lookback "[1,None]"
```

### Python

When using the portfolio class, the following code can be used to get the returns of a portfolio.

```python
from folioflex import config, portfolio
config_path = "portfolio.ini"
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

## Other Tools
### Jupyter Lab Usage

To have conda environments work with Jupyter Notebooks a kernel needs to be defined. This can be done defining a kernel, shown below when
in the conda environment.

```
python -m ipykernel install --user --name=folioflex
```
### Logging

If wanting to get more detail in output of messages the logging can increased
```python
import logging
logger = logging.getLogger('folioflex.portfolio.portfolio')
logger.setLevel(logging.WARNING)  # default: only print WARNINGS and above
logger.setLevel(logging.CRITICAL)  # disable printing
logger.setLevel(logging.DEBUG)  # verbose: print errors & debug info
```

### Coverage

To see the test coverage the following command is run in the root directory. This is also documented in the `.coveragerc` file.
```
pytest --cov=folioflex --cov-report=html
```

<hr>

[Go to Top](#table-of-contents)