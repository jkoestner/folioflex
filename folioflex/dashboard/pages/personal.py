"""Personal dashboard."""

from io import StringIO

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from celery.result import AsyncResult
from dash import Input, Output, State, callback, dcc, html
from dash.dash_table.Format import Format, Scheme
from flask_login import current_user

from folioflex.dashboard.components import layouts
from folioflex.dashboard.utils import dashboard_helper
from folioflex.utils import config_helper, cq, custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/personal", title="folioflex - Personal", order=4)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/

# list of portfolios
portfolio_list = list(
    config_helper.get_config_options("config.yml", "investments").keys()
)
value = "static"
if value in portfolio_list:
    portfolio_list.remove(value)


def layout():
    """Create layout for the personal dashboard."""
    if not current_user.is_authenticated:
        return html.Div(["Please ", dcc.Link("login", href="/login"), " to continue"])
    return dbc.Container(
        [
            html.H2("Personal Dashboard", className="text-center my-4"),
            # lookback
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Lookback"),
                            dbc.Input(
                                id="lookback-input",
                                placeholder="Enter Lookback...",
                                type="number",
                                style={"marginRight": "10px"},
                            ),
                        ],
                        width=3,
                    ),
                ],
                className="mb-4",
                justify="center",
            ),
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        title="Portfolio Manager",
                        children=[
                            # manager button
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Initialize Manager",
                                            id="manager-initialize",
                                            n_clicks=0,
                                            color="primary",
                                        ),
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        html.Div(id="manager_refresh_text"),
                                        width="auto",
                                    ),
                                ],
                                align="center",
                            ),
                            html.Br(),
                            # manager table
                            dcc.Loading(
                                id="loading-manager-table",
                                type="default",
                                children=html.Div(id="manager_table_container"),
                            ),
                        ],
                    ),
                    dbc.AccordionItem(
                        title="Portfolio",
                        children=[
                            # portfolio button
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Initialize Portfolio",
                                            id="personal-initialize",
                                            n_clicks=0,
                                            color="primary",
                                        ),
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        html.Div(id="personal_refresh_text"),
                                        width="auto",
                                    ),
                                ],
                                align="center",
                            ),
                            html.Br(),
                            # portfolio dropdowns
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Portfolio"),
                                            dcc.Dropdown(
                                                portfolio_list,
                                                placeholder="Select Portfolio",
                                                id="personal-dropdown",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Graph Type"),
                                            dcc.Dropdown(
                                                [
                                                    "change",
                                                    "return",
                                                    "cost",
                                                    "market_value",
                                                ],
                                                value="change",
                                                id="personal-view-type",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ],
                                align="center",
                            ),
                            html.Br(),
                            # graph
                            dcc.Loading(
                                id="loading-personal-graph",
                                type="default",
                                children=dcc.Graph(id="personal_graph"),
                            ),
                            html.Br(),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Time Period"),
                                            dcc.RangeSlider(
                                                id="personal_slider",
                                                tooltip={
                                                    "always_visible": True,
                                                    "placement": "bottom",
                                                },
                                                min=0,
                                                max=10,
                                                value=[0, 100],
                                                marks={
                                                    i: str(i) for i in range(0, 101, 10)
                                                },
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                            html.Br(),
                            # performance table
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5("Performance Table")),
                                    dbc.CardBody(
                                        dcc.Loading(
                                            id="loading-performance-table",
                                            type="default",
                                            children=html.Div(
                                                id="personal_performance_table_container"
                                            ),
                                        ),
                                    ),
                                ],
                                className="mt-4",
                            ),
                            html.Br(),
                            # transactions table
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5("Transactions Table")),
                                    dbc.CardBody(
                                        dcc.Loading(
                                            id="loading-transactions-table",
                                            type="default",
                                            children=html.Div(
                                                id="personal_transaction_table_container"
                                            ),
                                        ),
                                    ),
                                ],
                                className="mt-4",
                            ),
                        ],
                    ),
                ],
                start_collapsed=True,
            ),
            # adding variables needed that are used in callbacks
            *dashboard_helper.get_defaults(),
        ],
        fluid=True,
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/
#


# portfolio manager
@callback(
    Output("manager-task-id", "children"),
    Input("manager-initialize", "n_clicks"),
    State("lookback-input", "value"),
)
def initialize_ManagerTable(n_clicks, lookback):
    """Initialize the Portfolio Manager table."""
    if n_clicks == 0:
        manager_task_id = "none"
    else:
        config_file = "config.yml"
        task = cq.manager_query.delay(config_file, lookback)
        manager_task_id = task.id
    return manager_task_id


@callback(
    Output("manager_refresh_text", "children"),
    Input("manager-task-status", "children"),
)
def manager_refresh_text(manager_task_status):
    """Display the status text for the manager table."""
    return manager_task_status


@callback(
    Output("manager-task-status", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("manager-task-id", "children"),
    ],
    State("manager-task-status", "children"),
)
def manager_status_check(n_intervals, manager_task_id, manager_task_status):
    """Check the status of the manager task."""
    if manager_task_id != "none":
        task = AsyncResult(manager_task_id, app=cq.celery_app)
        manager_task_status = task.status
    else:
        manager_task_status = "waiting"
    return manager_task_status


@callback(
    Output("manager_table_container", "children"),
    Input("manager-task-status", "children"),
    State("manager-task-id", "children"),
)
def update_ManagerTable(manager_task_status, manager_task_id):
    """Update the Manager Table."""
    if manager_task_status == "SUCCESS":
        task = AsyncResult(manager_task_id, app=cq.celery_app)
        cq_pm = task.result
        cq_pm = pd.read_json(StringIO(cq_pm)).reset_index()
        cq_pm["lookback_date"] = pd.to_datetime(cq_pm["lookback_date"], unit="ms")
        columns = [
            {
                "name": i,
                "id": i,
                **(
                    {
                        "type": "numeric",
                        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
                    }
                    if cq_pm[i].dtype == "float64"
                    else {}
                ),
            }
            for i in cq_pm.columns
        ]
        data = cq_pm.to_dict("records")
        manager_table = dashboard_helper.create_datatable(columns, data)
        return manager_table
    else:
        return html.Div()


# portfolio
@callback(
    Output("personal-task-id", "children"),
    Input("personal-initialize", "n_clicks"),
    [
        State("personal-dropdown", "value"),
        State("lookback-input", "value"),
    ],
)
def initialize_PersonalGraph(n_clicks, dropdown, lookback):
    """Initialize the Personal Portfolio data."""
    if n_clicks == 0:
        personal_task_id = "none"
    else:
        config_file = "config.yml"
        personal_task = cq.portfolio_query.delay(
            config_file=config_file, broker=dropdown, lookback=lookback
        )
        personal_task_id = personal_task.id
    return personal_task_id


@callback(
    Output("personal_refresh_text", "children"),
    Input("personal-task-status", "children"),
)
def personal_refresh_text(personal_task_status):
    """Display the status text for the personal portfolio."""
    return personal_task_status


@callback(
    Output("personal-task-status", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("personal-task-id", "children"),
    ],
    State("personal-task-status", "children"),
)
def personal_status_check(n_intervals, personal_task_id, personal_task_status):
    """Check the status of the personal task."""
    if personal_task_id != "none":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        personal_task_status = personal_task.status
    else:
        personal_task_status = "waiting"
    return personal_task_status


@callback(
    [
        Output("personal_graph", "figure"),
        Output("personal_performance_table_container", "children"),
        Output("personal_transaction_table_container", "children"),
    ],
    [
        Input("personal-task-status", "children"),
        Input("personal-view-type", "value"),
        Input("personal_slider", "value"),
    ],
    State("personal-task-id", "children"),
)
def update_PersonalContent(
    personal_task_status, graph_type, slider_value, personal_task_id
):
    """Update the Personal Portfolio content."""
    if personal_task_status == "SUCCESS":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        cq_portfolio_dict = personal_task.result

        # Process graph data
        fig = dashboard_helper.update_graph(
            slider_value,
            pd.read_json(StringIO(cq_portfolio_dict["view_return"])),
            pd.read_json(StringIO(cq_portfolio_dict["view_cost"])),
            pd.read_json(StringIO(cq_portfolio_dict["view_market_value"])),
            graph_type,
        )

        # Process performance table
        performance = pd.read_json(StringIO(cq_portfolio_dict["performance"]))
        performance["lookback_date"] = pd.to_datetime(
            performance["lookback_date"], unit="ms"
        )
        performance = performance[performance["market_value"] != 0].sort_values(
            "return", ascending=False
        )
        columns_perf = layouts.performance_fmt
        data_perf = performance.to_dict("records")
        performance_table = dashboard_helper.create_datatable(columns_perf, data_perf)

        # Process transactions table
        transactions = pd.read_json(StringIO(cq_portfolio_dict["transactions"]))
        columns_trans = layouts.transactions_fmt
        data_trans = transactions.to_dict("records")
        transactions_table = dashboard_helper.create_datatable(
            columns_trans, data_trans
        )

        return fig, performance_table, transactions_table
    else:
        fig = {"data": [], "layout": go.Layout(hovermode="closest")}
        return fig, html.Div(), html.Div()


@callback(
    [
        Output("personal_slider", "min"),
        Output("personal_slider", "max"),
        Output("personal_slider", "value"),
        Output("personal_slider", "marks"),
    ],
    Input("personal-task-status", "children"),
    State("personal-task-id", "children"),
)
def update_PersonalSlider(personal_task_status, personal_task_id):
    """Update the Personal Portfolio slider."""
    if personal_task_status == "SUCCESS":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        cq_portfolio_dict = personal_task.result
        return_view = pd.read_json(StringIO(cq_portfolio_dict["view_return"]))
        min_value, max_value, value, marks = dashboard_helper.get_slider_values(
            return_view.index
        )
        return min_value, max_value, value, marks
    else:
        min_value = 0
        max_value = 100
        value = [0, 100]
        marks = {i: str(i) for i in range(0, 101, 10)}
        return min_value, max_value, value, marks
