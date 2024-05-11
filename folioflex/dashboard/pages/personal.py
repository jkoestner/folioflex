"""Personal dashboard."""

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from celery.result import AsyncResult
from dash import Input, Output, State, callback, dash_table, dcc, html
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


portfolio_list = config_helper.get_config("portfolio_personal.ini").sections()
value = "static"
if value in portfolio_list:
    portfolio_list.remove(value)


def layout():
    """Create layout for the personal dashboard."""
    if not current_user.is_authenticated:
        return html.Div(["Please ", dcc.Link("login", href="/login"), " to continue"])
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            # ---------------------------------------------------------------
            html.Div(
                [
                    dbc.Col(
                        [
                            html.Label("Lookback", style={"paddingRight": "10px"}),
                            dcc.Input(
                                id="lookback-input",
                                placeholder="Enter Lookback...",
                                type="number",
                                style={"marginRight": "10px"},
                            ),
                        ]
                    ),
                ],
                style={"display": "flex", "alignItems": "center"},
                className="row",
            ),
            html.Div(
                [
                    html.P(),
                    dbc.Col(
                        [
                            html.Button(
                                "Portfolio Manager", id="manager-initialize", n_clicks=0
                            ),
                            html.Div(id="manager_refresh_text", children=""),
                        ]
                    ),
                    # creating table for portfolio manager
                    html.Label("Portfolio Manager Table"),
                    dash_table.DataTable(
                        id="manager_table",
                        sort_action="native",
                        page_action="native",
                    ),
                    html.P(),
                ],
                className="row",
            ),
            html.Div(
                [
                    # initializing the portfolio
                    dbc.Col(
                        [
                            html.Button(
                                "Portfolio", id="personal-initialize", n_clicks=0
                            ),
                            dcc.Dropdown(
                                portfolio_list,
                                id="personal-dropdown",
                            ),
                            html.Div(id="personal_refresh_text", children=""),
                        ]
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
                    # creating table for performance
                    html.Label("Performance Table"),
                    dash_table.DataTable(
                        id="personal_perfomance_table",
                        sort_action="native",
                        page_action="native",
                    ),
                    html.P(),
                    html.P(),
                    # creating table for transactions
                    html.Label("Transactions Table"),
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


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# initializing workers
@callback(
    Output("personal-task-id", "children"),
    Input("personal-initialize", "n_clicks"),
    [
        State("personal-dropdown", "value"),
        State("lookback-input", "value"),
    ],
)
def initialize_PersonalGraph(n_clicks, dropdown, lookback):
    """Provide personal graph."""
    if n_clicks == 0:
        personal_task_id = "none"
    else:
        config_file = "portfolio_personal.ini"

        personal_task = cq.portfolio_query.delay(
            config_file=config_file, broker=dropdown, lookback=lookback
        )
        personal_task_id = personal_task.id

    return personal_task_id


# text
@callback(
    Output("personal_refresh_text", "children"),
    Input("personal-task-status", "children"),
)
def personal_refresh_text(personal_task_status):
    """Provide text for personal graph."""
    return personal_task_status


@callback(
    Output("personal-task-status", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("personal-task-id", "children"),
    ],
    [
        State("personal-task-status", "children"),
    ],
)
def personal_status_check(n_intervals, personal_task_id, personal_task_status):
    """Provide status check."""
    if personal_task_id != "none":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        personal_task_status = personal_task.status

    else:
        personal_task_status = "waiting"
    return personal_task_status


@callback(
    [
        Output("personal-portfolio-tx", "data"),
        Output("personal-status", "children"),
    ],
    Input("personal-task-status", "children"),
    State("personal-task-id", "children"),
)
def personal_get_results(personal_task_status, personal_task_id):
    """Provide status results."""
    if personal_task_status == "SUCCESS":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        personal_portfolio_tx = personal_task.result
        personal_status = "ready"
    else:
        personal_status = "none"
        personal_portfolio_tx = None

    return personal_portfolio_tx, personal_status


# graph
@callback(
    Output("personal_graph", "figure"),
    [
        Input("personal_slider", "value"),
    ],
    [
        State("personal-status", "children"),
        State("personal-portfolio-tx", "data"),
    ],
)
def update_PersonalGraph(slide_value, personal_status, cq_portfolio_dict):
    """Provide personal graph."""
    if personal_status == "ready":
        fig = dashboard_helper.update_graph(
            slide_value,
            pd.read_json(cq_portfolio_dict["view_return"]),
            pd.read_json(cq_portfolio_dict["view_cost"]),
        )
    else:
        "could not load"
        fig = {"data": [], "layout": go.Layout(hovermode="closest")}

    return fig


@callback(
    [
        Output("personal_slider", "min"),
        Output("personal_slider", "max"),
        Output("personal_slider", "value"),
        Output("personal_slider", "marks"),
    ],
    [Input("personal-status", "children")],
    [State("personal-portfolio-tx", "data")],
)
def update_PersonalSlider(personal_status, cq_portfolio_dict):
    """Provide sector data table."""
    if personal_status == "ready":
        return_view = pd.read_json(cq_portfolio_dict["view_return"])
        min, max, value, marks = dashboard_helper.get_slider_values(return_view.index)
    else:
        min = 0
        max = 100
        value = [0, 100]
        marks = {i: str(i) for i in range(0, 101, 10)}

    return min, max, value, marks


# performance table
@callback(
    [
        Output("personal_perfomance_table", "columns"),
        Output("personal_perfomance_table", "data"),
    ],
    [
        Input("personal-status", "children"),
    ],
    [
        State("personal-portfolio-tx", "data"),
    ],
)
def update_PersonalPerformance(personal_status, cq_portfolio_dict):
    """Provide personal performance table."""
    if personal_status == "ready":
        performance = pd.read_json(cq_portfolio_dict["performance"])
        performance["lookback_date"] = pd.to_datetime(
            performance["lookback_date"], unit="ms"
        )
        performance = performance[performance["market_value"] != 0].sort_values(
            "return", ascending=False
        )

        performance_table = layouts.performance_fmt, performance.to_dict("records")
    else:
        performance_table = (None, None)

    return performance_table


# transactions table
@callback(
    [
        Output("personal_transaction_table", "columns"),
        Output("personal_transaction_table", "data"),
    ],
    [
        Input("personal-status", "children"),
    ],
    [
        State("personal-portfolio-tx", "data"),
    ],
)
def update_PersonalTransaction(personal_status, cq_portfolio_dict):
    """Provide personal transaction table."""
    if personal_status == "ready":
        transactions = pd.read_json(cq_portfolio_dict["transactions"])
        transaction_table = layouts.transactions_fmt, transactions.to_dict("records")
    else:
        transaction_table = (None, None)

    return transaction_table


# ------------------------------------------------------------------
# Portfolio Manager
# initializing workers
@callback(
    Output("manager-task-id", "children"),
    Input("manager-initialize", "n_clicks"),
    State("lookback-input", "value"),
)
def initialize_ManagerTable(n_clicks, lookback):
    """Provide sector analysis graph."""
    if n_clicks == 0:
        manager_task_id = "none"
    else:
        config_file = "portfolio_personal.ini"
        task = cq.manager_query.delay(config_file, lookback)
        manager_task_id = task.id
        print(f"initializing manager table - {manager_task_id}")
    return manager_task_id


# text
@callback(
    Output("manager_refresh_text", "children"),
    Input("manager-task-status", "children"),
)
def manager_refresh_text(manager_task_status):
    """Provide text for manager table."""
    return manager_task_status


@callback(
    Output("manager-task-status", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("manager-task-id", "children"),
    ],
    [
        State("manager-task-status", "children"),
    ],
)
def manager_status_check(n_intervals, manager_task_id, manager_task_status):
    """Provide status check."""
    if manager_task_id != "none":
        task = AsyncResult(manager_task_id, app=cq.celery_app)
        manager_task_status = task.status

    else:
        manager_task_status = "waiting"
    return manager_task_status


@callback(
    [Output("manager-status", "children"), Output("manager-df", "children")],
    Input("manager-task-status", "children"),
    State("manager-task-id", "children"),
)
def manager_get_results(manager_task_status, manager_task_id):
    """Provide status results."""
    if manager_task_status == "SUCCESS":
        task = AsyncResult(manager_task_id, app=cq.celery_app)
        cq_pm = task.result
        manager_status = "ready"
    else:
        cq_pm = None
        manager_status = "none"

    return manager_status, cq_pm


# manager table
@callback(
    [
        Output("manager_table", "columns"),
        Output("manager_table", "data"),
    ],
    [
        Input("manager-status", "children"),
    ],
    [
        State("manager-df", "children"),
    ],
)
def update_ManagerTable(manager_status, cq_pm):
    """Provide personal performance table."""
    if manager_status == "ready":
        cq_pm = pd.read_json(cq_pm).reset_index()
        cq_pm["lookback_date"] = pd.to_datetime(cq_pm["lookback_date"], unit="ms")
        # formatting floats
        # TODO: put this in dashboard_helper function
        manager_table = (
            [
                {
                    "name": i,
                    "id": i,
                    **(
                        {
                            "type": "numeric",
                            "format": Format(precision=2, scheme=Scheme.fixed).group(
                                True
                            ),
                        }
                        if cq_pm[i].dtype == "float64"
                        else {}
                    ),
                }
                for i in cq_pm.columns
            ],
            cq_pm.to_dict("records"),
        )
    else:
        manager_table = (None, None)

    return manager_table
