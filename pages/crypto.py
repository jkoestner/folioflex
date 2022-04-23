import dash
from dash import dash_table
from dash import dcc
from dash import html
import json
import os
from urllib import request
from pages import utils

IEX_API_LIVE = os.environ["IEX_API_LIVE"]
IEX_API_SANDBOX = os.environ["IEX_API_SANDBOX"]

# Creating the dash app
btc = json.loads(
    request.urlopen(
        "https://cloud.iexapis.com/stable/crypto/btcusd/price?token=" + IEX_API_LIVE
    )
    .read()
    .decode("utf8")
)["price"]

ape = json.loads(
    request.urlopen(
        "https://cloud.iexapis.com/stable/crypto/apeusdt/price?token=" + IEX_API_LIVE
    )
    .read()
    .decode("utf8")
)["price"]

eth = json.loads(
    request.urlopen(
        "https://cloud.iexapis.com/stable/crypto/ethusd/price?token=" + IEX_API_LIVE
    )
    .read()
    .decode("utf8")
)["price"]

layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                html.Label("Crypto Analysis"),
                html.P(),
                dcc.Input(id="crypto-input", placeholder="Enter Coin...", type="text"),
                html.Button(id="crypto-quote-button", children="Crypto Quote Submit"),
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
                html.Label(btc),
                html.P(),
                html.Label("APE:"),
                html.Label(ape),
                html.P(),
                html.Label("ETH:"),
                html.Label(eth),
            ],
            className="three columns",
        ),
    ]
)
