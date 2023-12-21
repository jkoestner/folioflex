"""Personal dashboard."""

from dash import dash_table, dcc, html

from folioflex.dashboard import dashboard_helper
from folioflex.utils import config_helper

portfolio_list = config_helper.get_config("portfolio_personal.ini").sections()
value = "static"
if value in portfolio_list:
    portfolio_list.remove(value)


def layout(login_status, login_alert):
    """Create layout for the personal dashboard."""
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            dcc.Store(id="login-status", data=login_status),
            html.Div(id="login-alert", children=login_alert, style={"display": "none"}),
            # ---------------------------------------------------------------
            html.Div(
                [
                    dashboard_helper.get_menu(),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Label("Lookback", style={"paddingRight": "10px"}),
                    dcc.Input(
                        id="lookback-input",
                        placeholder="Enter Lookback...",
                        type="number",
                        style={"marginRight": "10px"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center"},
                className="row",
            ),
            html.Div(
                [
                    html.P(),
                    html.Button(
                        "Portfolio Manager", id="manager-initialize", n_clicks=0
                    ),
                    html.Div(id="manager_refresh_text", children=""),
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
                    html.Button("Portfolio", id="personal-initialize", n_clicks=0),
                    dcc.Dropdown(
                        portfolio_list,
                        id="personal-dropdown",
                    ),
                    html.Div(id="personal_refresh_text", children=""),
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
