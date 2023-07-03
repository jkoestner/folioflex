"""Utilities for app.

Provides functions for common used functions in app.
"""

import datetime
import os
import pandas as pd
import plotly.graph_objs as go

from dash import dcc
from dash import html
from dateutil.relativedelta import relativedelta


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


def getMarks(start, end, nth=365):
    """Return Nth marks for labeling.

    Parameters
    ----------
    start : date
        the minimum date of series
    end : date
        the maximum date of series
    nth : int
        the range to create a new mark

    Returns
    ----------
    marks : series
        the values that will have marks
    """
    result = []
    while start <= end:
        result.append(start)
        start += relativedelta(years=1)

    marks = {
        int(unix_time_millis(date)): (str(date.strftime("%Y-%m"))) for date in result
    }

    return marks


def get_slider_values(daterange):
    """Return slider values.

    Parameters
    ----------
    daterange : series
        series of dates to calculate values on

    Returns
    ----------
    min : date
        minimum date
    max : date
        maximum date
    value : series
        values to use
    marks : series
        marks on slider
    """
    # due to range step granularity, range needs to be extended to be inclusive of ends
    min = unix_time_millis(daterange.min()) - 1000000
    max = unix_time_millis(daterange.max()) + 1000000
    value = [
        unix_time_millis(daterange.min()),
        unix_time_millis(daterange.max()),
    ]
    marks = getMarks(daterange.min(), daterange.max())

    return min, max, value, marks


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


def update_graph(slide_value, view_return, view_cost):
    """Create a performance return graph.

    Parameters
    ----------
    slide_value : rangeslider objet
       Dash rangeslider object
    view_return : portfolio object
       the portfolio DataFrame to create figure on
    view_cost : portfolio object
       the transaction history portfolio DataFrame to create figure on

    Returns
    -------
    fig : Dash figure
       dash figure
    """
    res = []
    layout = go.Layout(hovermode="closest")

    view_cost = view_cost * -1

    return_grph = view_return[
        (unix_time_millis(view_return.index) > slide_value[0])
        & (unix_time_millis(view_return.index) <= slide_value[1])
    ].copy()

    cost_grph = view_cost[
        (unix_time_millis(view_cost.index) > slide_value[0])
        & (unix_time_millis(view_cost.index) <= slide_value[1])
    ].copy()

    for col in return_grph.columns:
        # calculates return % over time
        return_grph.loc[return_grph[col] != 0, "change"] = (
            return_grph[col] + cost_grph[col]
        ) / cost_grph[col] - 1
        return_grph.drop([col], axis=1, inplace=True)
        return_grph = return_grph.rename(columns={"change": col})
        res.append(
            go.Scatter(
                x=return_grph.index, y=return_grph[col].values.tolist(), name=col
            )
        )

    fig = dict(data=res, layout=layout)

    return fig
