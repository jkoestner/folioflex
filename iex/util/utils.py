"""Utilities for app.

Provides functions for common used functions in app.
"""

import datetime
import os
import pandas as pd
import yfinance as yf

from dash import dcc
from dash import html
from dateutil.relativedelta import relativedelta

from iex.util import layouts


def get_menu():
    """Provide menu for pages."""
    menu = html.Div(
        [
            dcc.Link(
                "Stocks   ",
                href="/stocks",
            ),
            dcc.Link(
                "Sectors   ",
                href="/sectors",
                style={"padding": 10},
            ),
            dcc.Link(
                "Ideas   ",
                href="/ideas",
                style={"padding": 10},
            ),
            dcc.Link(
                "Macro   ",
                href="/macro",
                style={"padding": 10},
            ),
            dcc.Link(
                "Tracker   ",
                href="/tracker",
                style={"padding": 10},
            ),
            dcc.Link(
                "Crypto   ",
                href="/crypto",
                style={"padding": 10},
            ),
        ]
    )
    return menu


def make_dash_table(df):
    """Return a dash definition of an HTML table for a Pandas dataframe."""
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table


def unix_time_millis(dt):
    """Convert unix timestamp to seconds."""
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()


def unixToDatetime(unix):
    """Convert unix timestamp to datetime."""
    return pd.to_datetime(unix, unit="s")


def getMarks(start, end, Nth=365):
    """Return the marks for labeling.

    Every Nth value will be used.
    """
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += relativedelta(years=1)
    return {
        int(unix_time_millis(date)): (str(date.strftime("%Y-%m"))) for date in result
    }


def get_remote_path():
    """Provide the remote path.

    Returns
    -------
    remote_path : str
       path that should be used depending on local or heroku
    """
    if os.path.isfile(r"/app/files/transactions.xlsx"):
        remote_path = r"/app/files/"

    elif os.path.isfile(r"files/transactions.xlsx"):
        remote_path = r"files/"

    else:
        remote_path = "No files found"

    return remote_path


def sector_query():
    """Provide the sector historical stock prices.

    Returns
    -------
    sector_close : dataframe
       provides the list of prices for historical prices
    """
    sector_close = yf.download(layouts.sector_list, start="2018-01-01")

    return sector_close["Adj Close"]
