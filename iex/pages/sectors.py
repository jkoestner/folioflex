"""Sector dashboard."""

import pandas as pd

from dash import dash_table
from dash import dcc
from dash import html

from iex.util import constants, utils

# Sector URL
urlsec = (
    "https://cloud.iexapis.com/stable/ref-data/sectors?token=" + constants.iex_api_live
)
sectors = pd.read_json(urlsec, orient="columns")
sectors["name"] = sectors["name"].str.replace(" ", "%20")

# Sector Performance
urlsecmap = (
    "https://www.alphavantage.co/query?function=SECTOR&apikey="
    + constants.alpha_vantage_api
)
secmap = pd.read_json(urlsecmap, orient="columns")
secmap = secmap.iloc[2:, 1:]
secmap = secmap.reset_index()
cols = secmap.columns.drop("index")
secmap[cols] = secmap[cols].replace("%", "", regex=True).astype(float)

# Creating the dash app

layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                html.Button("Sector initialize", id="sector-initialize", n_clicks=0),
                html.Div(id="refresh_text", children="none"),
                # graph
                dcc.Graph(
                    id="Sector-Graph",
                ),
                # range slider
                html.P(
                    [
                        html.Label("Time Period"),
                        dcc.RangeSlider(
                            id="slider",
                            tooltip="always_visible",
                            min=0,
                            max=10,
                            value=[0, 10],
                            marks=1,
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
                # creating table for sector perfomance
                html.Label("Sector Performance"),
                dash_table.DataTable(
                    id="sector-performance",
                    sort_action="native",
                    columns=[{"name": i, "id": i} for i in secmap.columns],
                    data=secmap.to_dict("records"),
                ),
                html.P(),
                # heatmap graph
                html.Button("Heatmap initialize", id="heatmap-initialize", n_clicks=0),
                dcc.Graph(
                    id="Heatmap-Graph",
                ),
                html.P(),
                # creating dropdown menu
                html.Label("Sectors Dropdown"),
                dcc.Dropdown(
                    id="sector-dropdown",
                    options=[{"label": i, "value": i} for i in sectors.name.unique()],
                    multi=False,
                    placeholder="Select Sector...",
                ),
                # creating table that is based on dropdown menu
                html.P(),
                html.Label("Sector Table"),
                dash_table.DataTable(
                    id="sector-table",
                    filter_action="native",
                    sort_action="native",
                    page_action="native",
                ),
            ],
            className="row",
        ),
    ]
)
