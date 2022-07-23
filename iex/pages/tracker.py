"""Tracker dashboard."""

from dash import dash_table
from dash import dcc
from dash import html

from iex.util import constants, utils

tracker_portfolio = constants.tracker_portfolio

performance = tracker_portfolio.get_performance().reset_index()
transactions = tracker_portfolio.transactions

# Creating the dash app
layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                # graph
                html.P(),
                dcc.Dropdown(
                    id="Tracker-Dropdown",
                    options=["return", "market_value"],
                    value="return",
                ),
                html.P(),
                dcc.Graph(
                    id="Tracker-Graph",
                ),
                html.P(),
                # creating table for performance
                html.Label("Performance"),
                dash_table.DataTable(
                    id="perfomance-table",
                    sort_action="native",
                    columns=[{"name": i, "id": i} for i in performance.columns],
                    data=performance.to_dict("records"),
                ),
                html.P(),
                html.P(),
                # creating table for transactions
                html.Label("Transactions"),
                dash_table.DataTable(
                    id="transaction-table",
                    sort_action="native",
                    columns=[{"name": i, "id": i} for i in transactions.columns],
                    data=transactions.to_dict("records"),
                ),
                html.P(),
            ],
            className="row",
        ),
    ]
)
