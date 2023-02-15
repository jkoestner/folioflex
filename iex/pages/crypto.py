"""Crypto dashboard."""

import json

from dash import dash_table
from dash import dcc
from dash import html
from urllib import request

from iex.util import constants, utils

# Creating the dash app

layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                html.Label("Crypto Analysis"),
                html.P(),
                dcc.Input(id="crypto-input", placeholder="Enter Coin...", type="text"),
                html.Button(
                    "Crypto Quote Submit", id="crypto-quote-button", n_clicks=0
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # creating quote information
                        dash_table.DataTable(
                            id="crypto-quote-table",
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
                # crypto prices
                html.Label("BTC:"),
                html.Label("iex removed"),
                html.P(),
                html.Label("APE:"),
                html.Label("iex removed"),
                html.P(),
                html.Label("ETH:"),
                html.Label("iex removed"),
            ],
            className="three columns",
        ),
    ]
)
