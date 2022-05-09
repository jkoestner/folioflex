from dash import dash_table
from dash import dcc
from dash import html
import os

import function
from pages import utils

if os.path.isfile(r"/app/files/transactions.xlsx"):
    tx_file = r"/app/files/transactions.xlsx"

else:
    tx_file = r"files/transactions.xlsx"

tx_df, portfolio, performance, cost = function.get_portfolio_and_transaction(tx_file)
daterange = portfolio.index
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
                    columns=[{"name": i, "id": i} for i in tx_df.columns],
                    data=tx_df.to_dict("records"),
                ),
                html.P(),
            ],
            className="row",
        ),
    ]
)
