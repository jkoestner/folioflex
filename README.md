# IEX
IEX cloud finance

![workflow badge](https://github.com/jkoestner/iex/actions/workflows/main.yml/badge.svg)

This is an app built with https://dashboard.heroku.com/ as the host

The app can be seen at https://koestner.herokuapp.com/

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

Data sources:
- https://iexcloud.io/
- https://www.alphavantage.co
- https://pypi.org/project/yahoo-finance/