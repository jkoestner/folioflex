"""Worker connections."""

import os
import redis
import yfinance as yf

from rq import Worker, Queue, Connection

from iex.util import layouts, portfolio

listen = ["high", "default", "low"]

if os.path.isfile(r"/app/files/transactions.xlsx"):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
else:
    # if debugging locally will need a redis
    redis_url = os.getenv("LOCAL_REDIS")

conn = redis.from_url(redis_url)

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()


def sector_query(start="2018-01-01"):
    """Provide the sector historical stock prices.

    Parameters
    ----------
    start : date
       start date of series

    Returns
    -------
    sector_close : series
       provides the list of prices for historical prices
    """
    sector_close = yf.download(layouts.list_sector, start=start)

    return sector_close["Adj Close"]


def portfolio_query(tx_file):
    """Query for worker to generate portfolio.

    Parameters
    ----------
    tx_file : str
       file to create

    Returns
    -------
    personal_portfolio : portfolio object
       provides the portfolio class
    """
    personal_portfolio = portfolio.portfolio(
        tx_file,
        filter_type=["Cash", "Dividend"],
        funds=["BLKEQIX", "TRPILCG", "TRPSV", "LIPIX", "BLKRVIX", "BLKRGIX", "HLIEIX"],
        other_fields=["Broker", "Account"],
    )

    return personal_portfolio
