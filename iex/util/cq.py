"""Worker connections.

note: there are two resources that are needed to use the worker processes.

1. redis server - this is the message broker that is used to communicate between the
worker and the main process.

2. worker - this is the process that will be used to execute the tasks.  The worker
will be listening to the redis server for tasks to execute.

To run the worker process locally from the root directory, use the following command:
   celery -A iex.util.cq worker --pool=solo -l info

If wanting to look at monitoring celery, use the following command which will be
available at http://localhost:5555:
    celery -A iex.util.cq flower
"""

import os
import yfinance as yf

from celery import Celery

from iex.util import layouts
from iex.portfolio import portfolio

if os.path.isfile(r"/app/files/transactions.xlsx"):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
else:
    # if debugging locally will need a redis
    redis_url = os.getenv("LOCAL_REDIS")

celery_app = Celery(
    "tasks",
    broker=redis_url,
    backend=redis_url,
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle"],
    result_expires=3600,
)


@celery_app.task
def sector_query(start="2023-01-01"):
    """Provide the sector historical stock prices.

    Parameters
    ----------
    start : date
       start date of series

    Returns
    -------
    cq_sector_close : json
       provides the list of prices for historical prices
    """
    sector_close = yf.download(layouts.list_sector, start=start)
    cq_sector_close = sector_close["Adj Close"].to_json()

    return cq_sector_close


@celery_app.task
def portfolio_query(tx_file, filter_broker=None, lookback=None):
    """Query for worker to generate portfolio.

    Parameters
    ----------
    tx_file : str
       file to create
    filter_broker : list (optional)
        the brokers to include in analysis
    lookback : int (optional)
        amount of days to lookback

    Returns
    -------
    cq_portfolio_dict : dict
       provides a dict of portfolio objects
    """
    personal_portfolio = portfolio.Portfolio(
        tx_file,
        filter_type=["Dividend"],
        filter_broker=filter_broker,
        funds=layouts.funds,
        delisted=layouts.delisted,
        other_fields=["broker"],
        benchmarks=["IVV"],
    )

    # get transactions that have portfolio informaiton as well
    transactions = personal_portfolio.transactions_history
    transactions = transactions[
        (transactions["units"] != 0) & (transactions["units"].notnull())
    ].sort_values(by="date", ascending=False)

    # provide results in dictionary
    cq_portfolio_dict = {}
    cq_portfolio_dict["transactions"] = transactions.to_json()
    cq_portfolio_dict["performance"] = (
        personal_portfolio.get_performance(lookback=lookback).reset_index().to_json()
    )
    cq_portfolio_dict["view_return"] = personal_portfolio.get_view(
        view="return"
    ).to_json()
    cq_portfolio_dict["view_cost"] = personal_portfolio.get_view(
        view="cumulative_cost"
    ).to_json()

    return cq_portfolio_dict


@celery_app.task
def manager_query(tx_file, lookback=None):
    """Query for worker to generate manager.

    Parameters
    ----------
    tx_file : str
       file to create
    lookback : int (optional)
        amount of days to lookback

    Returns
    -------
    cq_pm : json
       provides the portfolio manager performance
    """
    # constant variables used in program
    filter_type = ["Dividend"]
    funds = layouts.funds
    delisted = layouts.delisted
    other_fields = ["broker"]
    benchmarks = ["IVV"]

    # create portfolio objects
    pf = portfolio.Portfolio(
        tx_file,
        filter_type=filter_type,
        funds=funds,
        delisted=delisted,
        other_fields=other_fields,
        benchmarks=benchmarks,
        name="all",
    )
    fidelity = portfolio.Portfolio(
        tx_file,
        filter_type=filter_type,
        funds=funds,
        delisted=delisted,
        other_fields=other_fields,
        benchmarks=benchmarks,
        name="fidelity",
        filter_broker=["Fidelity"],
    )
    ib = portfolio.Portfolio(
        tx_file,
        filter_type=filter_type,
        funds=funds,
        delisted=delisted,
        other_fields=other_fields,
        benchmarks=benchmarks,
        name="ib",
        filter_broker=["IB"],
    )
    eiten = portfolio.Portfolio(
        tx_file,
        filter_type=filter_type,
        funds=funds,
        delisted=delisted,
        other_fields=other_fields,
        benchmarks=benchmarks,
        name="eiten",
        filter_broker=["IB-eiten"],
    )
    roth = portfolio.Portfolio(
        tx_file,
        filter_type=filter_type,
        funds=funds,
        delisted=delisted,
        other_fields=other_fields,
        benchmarks=benchmarks,
        name="roth",
        filter_broker=["Ally_Roth"],
    )
    company = portfolio.Portfolio(
        tx_file,
        filter_type=filter_type,
        funds=funds,
        delisted=delisted,
        other_fields=other_fields,
        benchmarks=benchmarks,
        name="company",
        filter_broker=["Company"],
    )
    portfolios = [pf, fidelity, ib, eiten, roth, company]
    pm = portfolio.Manager(portfolios)
    cq_pm = pm.get_summary(lookback=lookback).to_json()

    return cq_pm
