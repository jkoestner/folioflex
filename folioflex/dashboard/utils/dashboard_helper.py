"""
Utilities for app.

Provides functions for common used functions in app.
"""

import datetime

import pandas as pd
import plotly.graph_objs as go
from dash import dash_table, dcc, html
from dateutil.relativedelta import relativedelta

from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)


def get_defaults():
    """Provide default initializations for pages."""
    # TODO
    # These are needed so that the variable can be none. With some work
    # this could probably be removed and put in individual pages.
    defaults = (
        html.Div(id="task-status", children="none", style={"display": "none"}),
        html.Div(id="refresh_text", children="none", style={"display": "none"}),
        html.Div(id="task-id", children="none", style={"display": "none"}),
        html.Div(id="sector-status", children="none", style={"display": "none"}),
        html.Div(id="yf-data", children="none", style={"display": "none"}),
        html.Div(id="personal-task-status", children="none", style={"display": "none"}),
        html.Div(id="personal-task-id", children="none", style={"display": "none"}),
        html.Div(id="personal-status", children="none", style={"display": "none"}),
        dcc.Store(id="personal-portfolio-tx"),
        html.Div(id="manager-df", children="none", style={"display": "none"}),
        html.Div(id="manager-task-status", children="none", style={"display": "none"}),
        html.Div(id="manager-task-id", children="none", style={"display": "none"}),
        html.Div(id="manager-status", children="none", style={"display": "none"}),
        dcc.Interval(
            id="interval-component", interval=24 * 60 * 60 * 1000, n_intervals=0
        ),
    )
    return defaults


def make_dash_table(df):
    """Return a dash definition of an HTML table for a Pandas dataframe."""
    table = []
    for _index, row in df.iterrows():
        html_row = [html.Td([cell]) for cell in row]
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
    """
    Return Nth marks for labeling.

    Parameters
    ----------
    start : date
        the minimum date of series
    end : date
        the maximum date of series
    nth : int
        the range to create a new mark

    Returns
    -------
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
    """
    Return slider values.

    Parameters
    ----------
    daterange : series
        series of dates to calculate values on

    Returns
    -------
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


def update_graph(slide_value, view_return, view_cost, view_market, graph_type="change"):
    """
    Create a performance return graph.

    Parameters
    ----------
    slide_value : rangeslider objet
       Dash rangeslider object
    view_return : portfolio object
       the portfolio DataFrame to create figure on
    view_cost : portfolio object
       the transaction history portfolio DataFrame to create figure on
    view_market : portfolio object
         the market value portfolio DataFrame to create figure on
    graph_type : str
        the measure to graph ("change", "market_value", "cost", "return")

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

    market_grph = view_market[
        (unix_time_millis(view_market.index) > slide_value[0])
        & (unix_time_millis(view_market.index) <= slide_value[1])
    ].copy()

    if graph_type == "change":
        fig_df = return_grph
    elif graph_type == "market_value":
        fig_df = market_grph
    elif graph_type == "cost":
        fig_df = cost_grph
    elif graph_type == "return":
        fig_df = return_grph
    else:
        logger.warning("no graph type selected")
        fig_df = return_grph

    for col in fig_df.columns:
        if graph_type == "change":
            # calculates return % over time
            fig_df.loc[fig_df[col] != 0, "change"] = (
                fig_df[col] + cost_grph[col]
            ) / cost_grph[col] - 1
            fig_df = fig_df.drop([col], axis=1)
            fig_df = fig_df.rename(columns={"change": col})
        else:
            pass
        res.append(go.Scatter(x=fig_df.index, y=fig_df[col].values.tolist(), name=col))

    fig = {"data": res, "layout": layout}

    return fig


def create_datatable(columns, data):
    """Help function to create a styled DataTable."""
    return dash_table.DataTable(
        columns=columns,
        data=data,
        page_action="native",
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "5px",
            "minWidth": "100px",
            "width": "150px",
            "maxWidth": "300px",
            "whiteSpace": "normal",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)",
            }
        ],
        markdown_options={"html": True},
        sort_action="native",
        filter_action="native",
    )
