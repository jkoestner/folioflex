"""Sector dashboard."""

from io import StringIO

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
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
    return dbc.Container(
        [
            html.H2("Sector Analysis Dashboard", className="text-center my-4"),
            # sector graph
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Sector Performance")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Initialize Sector Data",
                                            id="sector-initialize",
                                            n_clicks=0,
                                            color="primary",
                                            className="mb-3 mb-md-0 w-100",
                                        ),
                                        xs=12,
                                        md="auto",
                                    ),
                                    dbc.Col(
                                        dcc.RangeSlider(
                                            id="slider",
                                            tooltip=dashboard_helper.get_slider_tooltip(),
                                            min=0,
                                            max=10,
                                            value=[0, 100],
                                            marks={
                                                i: str(i) for i in range(0, 101, 10)
                                            },
                                        ),
                                        xs=12,
                                        md=True,
                                        className="mt-3 px-4",
                                    ),
                                ],
                                align="center",
                            ),
                            html.Div(
                                id="slider-date-display",
                                className="text-center text-muted small mt-4",
                            ),
                            html.Div(id="refresh_text", style={"display": "none"}),
                            dcc.Loading(
                                id="loading-sector-graph",
                                children=dcc.Graph(id="Sector-Graph"),
                                custom_spinner=dmc.Skeleton(
                                    visible=True, h=450, w="100%"
                                ),
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # heatmap graph
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Market Heatmap")),
                    dbc.CardBody(
                        [
                            dbc.Button(
                                "Initialize Heatmap",
                                id="heatmap-initialize",
                                n_clicks=0,
                                color="primary",
                            ),
                            dcc.Loading(
                                id="loading-heatmap-graph",
                                children=dcc.Graph(id="Heatmap-Graph"),
                                custom_spinner=dmc.Skeleton(
                                    visible=True, h=450, w="100%"
                                ),
                            ),
                        ]
                    ),
                ]
            ),
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
        ],
        fluid=True,
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# sector Graph
@callback(
    Output("task-id", "children"),
    Input("sector-initialize", "n_clicks"),
)
def initialize_SectorGraph(n_clicks):
    """Initialize sector data fetching."""
    if n_clicks == 0:
        task_id = "none"
    else:
        task = cq.sector_query.delay()
        task_id = task.id

    return task_id


@callback(
    [Output("task-status", "children"), Output("refresh_text", "children")],
    [Input("task-id", "children"), Input("interval-component", "n_intervals")],
)
def status_check(task_id, n_intervals):
    """Check the status of the sector data task."""
    if task_id != "none":
        task = AsyncResult(task_id, app=cq.celery_app)
        task_status = task.status
    else:
        task_status = "waiting"
    return task_status, task_status


@callback(
    [Output("yf-data", "children"), Output("sector-status", "children")],
    Input("task-status", "children"),
    State("task-id", "children"),
)
def get_results(task_status, task_id):
    """Retrieve sector data when ready."""
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
    Input("sector-status", "children"),
    State("yf-data", "children"),
)
def update_SectorData(sector_status, yf_data):
    """Update the range slider based on sector data."""
    if sector_status == "ready":
        cq_sector_close = pd.read_json(StringIO(yf_data))
        min_value, max_value, value, marks = dashboard_helper.get_slider_values(
            cq_sector_close.index, nth=3
        )
    else:
        min_value = 0
        max_value = 100
        value = [0, 100]
        marks = {i: str(i) for i in range(0, 101, 10)}

    return min_value, max_value, value, marks


@callback(
    Output("Sector-Graph", "figure"),
    [Input("slider", "value"), Input("sector-status", "children")],
    State("yf-data", "children"),
)
def update_SectorGraph(slider_value, sector_status, yf_data):
    """Update the sector performance graph based on slider."""
    res = []
    layout = go.Layout(
        hovermode="closest",
        xaxis=dict(tickformat="%Y-%m-%d", type="date"),
        yaxis=dict(ticksuffix="%", title="Return (%)"),
        margin=dict(l=60, r=20, t=50, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        autosize=True,
        uirevision="sector-graph",
    )

    if sector_status == "ready" and slider_value != [0, 0]:
        cq_sector_close = pd.read_json(StringIO(yf_data))
        sector_data = cq_sector_close[
            (dashboard_helper.unix_time_millis(cq_sector_close.index) > slider_value[0])
            & (
                dashboard_helper.unix_time_millis(cq_sector_close.index)
                <= slider_value[1]
            )
        ].copy()

        for col in sector_data.columns:
            change = sector_data[col] / sector_data[col].iloc[0] - 1
            change_percentage = change * 100
            res.append(
                go.Scatter(
                    x=sector_data.index,
                    y=change_percentage,
                    name=col,
                    mode="lines",
                )
            )
    else:
        res = []

    fig = go.Figure(data=res, layout=layout)
    return fig


@callback(
    Output("slider-date-display", "children"),
    Input("slider", "value"),
)
def update_slider_display(slider_value):
    """Display the selected date range from the slider."""
    if not slider_value or slider_value == [0, 100]:
        return ""
    start = pd.to_datetime(slider_value[0], unit="s").strftime("%Y-%m-%d")
    end = pd.to_datetime(slider_value[1], unit="s").strftime("%Y-%m-%d")
    return f"{start} → {end}"


# heatmap Graph
@callback(
    Output("Heatmap-Graph", "figure"),
    Input("heatmap-initialize", "n_clicks"),
)
def initialize_HeatmapGraph(n_clicks):
    """Provide heatmap graph."""
    if n_clicks == 0:
        fig = go.Figure()
    else:
        fig = heatmap.get_heatmap()

    return fig
