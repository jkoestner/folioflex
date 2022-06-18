"""Tracker dashboard."""

from dash import dash_table
from dash import dcc
from dash import html

from iex.util import constants, portfolio, utils

tx_file = constants.remote_path + r"transactions.xlsx"
the_portfolio = portfolio.portfolio(
    tx_file, filter_type=["Cash", "Dividend"], funds=["BLKRK"]
)
portfolio_view = the_portfolio.portfolio_view
performance = the_portfolio.get_performance().reset_index()
transactions = the_portfolio.transactions

daterange = portfolio_view.index
min = utils.unix_time_millis(daterange.min())
max = utils.unix_time_millis(daterange.max())
value = [
    utils.unix_time_millis(daterange.min()),
    utils.unix_time_millis(daterange.max()),
]
marks = utils.getMarks(daterange.min(), daterange.max())

# Creating the dash app
layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                # graph
                dcc.Graph(
                    id="Tracker-Graph",
                ),
                # range slider
                html.P(
                    [
                        html.Label("Time Period"),
                        dcc.RangeSlider(
                            id="track_slider",
                            tooltip="always_visible",
                            min=min,
                            max=max,
                            value=value,
                            marks=marks,
                        ),
                    ],
                    style={
                        "width": "80%",
                        "fontSize": "20px",
                        "padding-left": "100px",
                        "display": "inline-block",
                    },
                ),
                html.P(),
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
