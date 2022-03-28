import dash
from dash import dash_table
from dash import dcc
from dash import html
import pandas as pd
from dash.dependencies import Input, Output, State
import os
import plotly.graph_objs as go
import datetime
from dateutil.relativedelta import relativedelta
from pages import utils, layouttab
from worker import conn
from rq.job import Job

IEX_API_LIVE = os.environ['IEX_API_LIVE']
IEX_API_SANDBOX = os.environ['IEX_API_SANDBOX']
ALPHAVANTAGE_API = os.environ['ALPHAVANTAGE_API']

# Sector URL
urlsec = "https://cloud.iexapis.com/stable/ref-data/sectors?token=" + IEX_API_LIVE
sectors = pd.read_json(urlsec, orient="columns")
sectors["name"] = sectors["name"].str.replace(" ", "%20")

# Sector Performance
urlsecmap = "https://www.alphavantage.co/query?function=SECTOR&apikey=" + ALPHAVANTAGE_API
secmap = pd.read_json(urlsecmap, orient="columns")
secmap = secmap.iloc[2:, 1:]
secmap = secmap.reset_index()


# Creating the dash app

layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                html.Button(id="sector-initialize", children="Sector initialize"),
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
                    # virtualization=True,
                    page_action="native",
                ),
            ],
            className="row",
        ),
    ]
)
