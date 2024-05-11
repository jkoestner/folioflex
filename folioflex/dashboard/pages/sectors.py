"""Sector dashboard."""

from io import StringIO

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from celery.result import AsyncResult
from dash import Input, Output, State, callback, dcc, html

from folioflex.dashboard.utils import dashboard_helper
from folioflex.portfolio import heatmap
from folioflex.utils import cq, custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/sectors", title="folioflex - Sectors", order=1)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Sectors layout."""
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            # ---------------------------------------------------------------
            dbc.Col(
                html.Button("Sector initialize", id="sector-initialize", n_clicks=0),
            ),
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
                        tooltip={"always_visible": True, "placement": "bottom"},
                        min=0,
                        max=10,
                        value=[0, 100],
                        marks={i: str(i) for i in range(0, 101, 10)},
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
            # heatmap graph
            dbc.Col(
                html.Button("Heatmap initialize", id="heatmap-initialize", n_clicks=0),
            ),
            dcc.Graph(
                id="Heatmap-Graph",
            ),
        ]
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# Sector Graph
@callback(
    Output("task-id", "children"),
    [Input(component_id="sector-initialize", component_property="n_clicks")],
)
def initialize_SectorGraph(n_clicks):
    """Provide sector analysis graph."""
    if n_clicks == 0:
        task_id = "none"
    else:
        task = cq.sector_query.delay()
        task_id = task.id

    return task_id


@callback(
    [Output("task-status", "children"), Output("refresh_text", "children")],
    [Input("interval-component", "n_intervals")],
    [State("task-id", "children"), State("task-status", "children")],
)
def status_check(n_intervals, task_id, task_status):
    """Provide status check."""
    if task_id != "none":
        task = AsyncResult(task_id, app=cq.celery_app)
        task_status = task.status
    else:
        task_status = "waiting"
    return task_status, task_status


@callback(
    [Output("yf-data", "children"), Output("sector-status", "children")],
    [Input("task-status", "children")],
    [State("task-id", "children")],
)
def get_results(task_status, task_id):
    """Provide status results."""
    if task_status == "SUCCESS":
        task = AsyncResult(task_id, app=cq.celery_app)
        cq_sector_close = task.result
        sector_status = "ready"
    else:
        sector_status = "none"
        cq_sector_close = None
    return cq_sector_close, sector_status


@callback(
    [
        Output("slider", "min"),
        Output("slider", "max"),
        Output("slider", "value"),
        Output("slider", "marks"),
    ],
    [Input("sector-status", "children")],
    [State("yf-data", "children")],
)
def update_SectorData(sector_status, yf_data):
    """Provide sector data table."""
    if sector_status == "ready":
        cq_sector_close = pd.read_json(StringIO(yf_data))
        min, max, value, marks = dashboard_helper.get_slider_values(
            cq_sector_close.index
        )
    else:
        min = 0
        max = 100
        value = [0, 100]
        marks = {i: str(i) for i in range(0, 101, 10)}

    return min, max, value, marks


@callback(
    Output("Sector-Graph", "figure"),
    [Input("slider", "value")],
    [State("yf-data", "children"), State("sector-status", "children")],
)
def update_SectorGraph(slide_value, yf_data, sector_status):
    """Provide sector graph."""
    res = []
    layout = go.Layout(hovermode="closest")

    if sector_status == "ready" and slide_value != 0:
        cq_sector_close = pd.read_json(StringIO(yf_data))
        sector_data = cq_sector_close[
            (dashboard_helper.unix_time_millis(cq_sector_close.index) > slide_value[0])
            & (
                dashboard_helper.unix_time_millis(cq_sector_close.index)
                <= slide_value[1]
            )
        ].copy()
        for col in sector_data.columns:
            sector_data["change"] = sector_data[col] / sector_data[col].iat[0] - 1
            sector_data = sector_data.drop([col], axis=1)
            sector_data["change"] = sector_data["change"].map("{0:.1%}".format)
            sector_data = sector_data.rename(columns={"change": col})
            res.append(
                go.Scatter(
                    x=sector_data.index, y=sector_data[col].values.tolist(), name=col
                )
            )
    else:
        "could not load"

    fig = {"data": res, "layout": layout}

    return fig


# Heatmap Graph
@callback(
    Output("Heatmap-Graph", "figure"),
    [Input(component_id="heatmap-initialize", component_property="n_clicks")],
)
def initialize_HeatmapGraph(n_clicks):
    """Provide heatmap graph."""
    if n_clicks == 0:
        fig = {"data": [], "layout": go.Layout(hovermode="closest")}
    else:
        fig = heatmap.get_heatmap()

    return fig
