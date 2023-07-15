"""Stocks dashboard."""

import datetime

from dash import dash_table
from dash import dcc
from dash import html

from iex.dashboard import utils

# Creating the dash app

layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                html.Label("Stock Analysis"),
                html.P(),
                dcc.Markdown(
                    """
                    A site to review for insider activity.
                    http://www.insiderinsights.com/free
                    """
                ),
                html.P(),
                dcc.Input(id="stock-input", placeholder="Enter Stock...", type="text"),
                html.Button("Active Submit", id="active-button", n_clicks=0),
                html.Button("Stock Submit", id="stock-button", n_clicks=0),
                html.Button("Quote Submit", id="quote-button", n_clicks=0),
                html.Button("Peer Submit", id="peer-button", n_clicks=0),
                html.Button("News Submit", id="news-button", n_clicks=0),
                html.Button(
                    "Insider Summary Submit", id="insider-summary-button", n_clicks=0
                ),
                html.Button(
                    "Insider Transactions Submit", id="insider-tx-button", n_clicks=0
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                dcc.DatePickerSingle(
                    id="date-input",
                    initial_visible_month=datetime.date.today(),
                    date=datetime.date.today(),
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # creating active information
                        html.P(),
                        dash_table.DataTable(
                            id="active-table",
                            page_action="native",
                            sort_action="native",
                        ),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # creating stock information
                        dash_table.DataTable(
                            id="stock-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
                html.Div(
                    [
                        # creating quote information
                        dash_table.DataTable(
                            id="quote-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
                html.Div(
                    [
                        # creating peer information
                        html.P(),
                        dash_table.DataTable(
                            id="peer-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # creating news information
                        html.P(),
                        dash_table.DataTable(
                            id="news-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # creating insider summary
                        html.P(),
                        dash_table.DataTable(
                            id="insider-summary-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # creating insider transactions
                        html.P(),
                        dash_table.DataTable(
                            id="insider-tx-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
    ]
)
