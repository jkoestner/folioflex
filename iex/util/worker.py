"""Worker connections.

note: there are two resources that are needed to use the worker processes.

1. redis server - this is the message broker that is used to communicate between the
worker and the main process.

2. worker - this is the process that will be used to execute the tasks.  The worker
will be listening to the redis server for tasks to execute.
"""

import os
import redis
import yfinance as yf

from rq import Worker, Queue, Connection

from iex.util import layouts
from iex.portfolio import portfolio

listen = ["high", "default", "low"]

if os.path.isfile(r"/app/files/transactions.xlsx"):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
else:
    # if debugging locally will need a redis
    redis_url = os.getenv("LOCAL_REDIS")

print(f"redis url: {redis_url}")
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


def test():
    return 1


def portfolio_query(tx_file, filter_broker=None):
    """Query for worker to generate portfolio.

    Parameters
    ----------
    tx_file : str
       file to create
    filter_broker : list (optional)
        the brokers to include in analysis

    Returns
    -------
    personal_portfolio_tx : dataframe
       provides the portfolio transaction history
    """
    personal_portfolio = portfolio.Portfolio(
        tx_file,
        filter_type=["Dividend"],
        filter_broker=filter_broker,
        funds=["BLKEQIX", "TRPILCG", "TRPSV", "LIPIX", "BLKRVIX", "BLKRGIX", "HLIEIX"],
        other_fields=["broker"],
        benchmarks=["IVV"],
    )
    personal_portfolio_tx = personal_portfolio.transactions_history

    return personal_portfolio_tx
