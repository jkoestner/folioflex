"""
Worker connections.

note: there are two resources that are needed to use the worker processes.

1. redis server - this is the message broker that is used to communicate between the
   worker and the main process. The redis server is referenced using environment
   variables `REDIS_URL` and `LOCAL_REDIS`.  The `REDIS_URL` is used when the
   application is deployed on web and the `LOCAL_REDIS` is used when debugging locally.

2. worker - this is the process that will be used to execute the tasks.  The worker
   will be listening to the redis server for tasks to execute.

To run the worker process locally from the root directory, use the following command:
   celery -A folioflex.utils.cq worker --pool=solo -l info

If wanting to look at monitoring celery, use the following command which is available
on localhost:5555:
   celery -A folioflex.utils.cq flower
"""

from datetime import datetime

import yfinance as yf
from celery import Celery

from folioflex.dashboard.components import layouts
from folioflex.portfolio import portfolio
from folioflex.utils import config_helper

celery_app = Celery(
    "tasks",
    broker=config_helper.REDIS_URL,
    backend=config_helper.REDIS_URL,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
)


@celery_app.task
def sector_query(start="2023-01-01"):
    """
    Provide the sector historical stock prices.

    Parameters
    ----------
    start : date
       start date of series

    Returns
    -------
    cq_sector_close : json
       provides the list of prices for historical prices
    """
    sector_close = yf.download(
        layouts.list_sector, start=start, end=datetime(2100, 1, 1)
    )
    cq_sector_close = sector_close["Adj Close"].to_json()

    return cq_sector_close


@celery_app.task
def portfolio_query(config_file, broker="all", lookback=None):
    """
    Query for worker to generate portfolio.

    Parameters
    ----------
    config_file : str
       config file name
    broker : str
        the brokers to include in analysis
    lookback : int (optional)
        amount of days to lookback

    Returns
    -------
    cq_portfolio_dict : dict
       provides a dict of portfolio objects
    """
    config_path = config_helper.CONFIG_PATH / config_file
    personal_portfolio = portfolio.Portfolio(config_path=config_path, portfolio=broker)

    # get transactions that have portfolio information as well
    transactions = personal_portfolio.transactions.head(10)

    # provide results in dictionary
    cq_portfolio_dict = {}
    cq_portfolio_dict["transactions"] = transactions.to_json()
    cq_portfolio_dict["performance"] = (
        personal_portfolio.get_performance(lookback=lookback).reset_index().to_json()
    )
    view_return = personal_portfolio.get_view(view="return", lookback=lookback)
    filtered_columns = [
        col for col in view_return.columns if "benchmark" in col or col == "portfolio"
    ]
    view_return = view_return[filtered_columns]
    cq_portfolio_dict["view_return"] = view_return.to_json()

    view_cost = personal_portfolio.get_view(view="cumulative_cost", lookback=lookback)
    view_cost = view_cost[filtered_columns]
    cq_portfolio_dict["view_cost"] = view_cost.to_json()

    view_market = personal_portfolio.get_view(view="market_value", lookback=lookback)
    view_market = view_market[filtered_columns]
    cq_portfolio_dict["view_market_value"] = view_market.to_json()

    return cq_portfolio_dict


@celery_app.task
def manager_query(config_file, lookbacks=None):
    """
    Query for worker to generate manager.

    Parameters
    ----------
    config_file : str
       config file name
    lookbacks : int (optional)
        amount of days to lookback

    Returns
    -------
    cq_pm : json
       provides the portfolio manager performance
    """
    config_path = config_helper.CONFIG_PATH / config_file

    pm = portfolio.Manager(config_path=config_path)
    cq_pm = pm.get_summary(lookbacks=lookbacks).to_json()

    return cq_pm
