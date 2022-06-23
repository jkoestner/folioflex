"""Personal dashboard."""

from dash import dash_table
from dash import dcc
from dash import html

from iex.util import constants, utils

personal_portfolio = constants.personal_portfolio
portfolio_view = personal_portfolio.portfolio_view
min, max, value, marks = utils.get_slider_values(portfolio_view.index)

# Creating the dash app
layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                # dropdown
                dcc.Dropdown(
                    [
                        "Total",
                        "Ally_Individual",
                        "Company",
                        "Fidelity",
                        "IB",
                        "Ally_Roth",
                    ],
                    "Total",
                    id="personal_dropdown",
                ),
                # graph
                dcc.Graph(
                    id="personal_graph",
                ),
                # range slider
                html.P(
                    [
                        html.Label("Time Period"),
                        dcc.RangeSlider(
                            id="personal_slider",
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
                    id="personal_perfomance_table",
                    sort_action="native",
                    page_action="native",
                ),
                html.P(),
                html.P(),
                # creating table for transactions
                html.Label("Transactions"),
                dash_table.DataTable(
                    id="personal_transaction_table",
                    sort_action="native",
                ),
                html.P(),
            ],
            className="row",
        ),
    ]
)
