"""Personal dashboard."""

from dash import dcc, html

from folioflex.dashboard import dashboard_helper


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
                    html.Label("Date (YYYY-MM)", style={"paddingRight": "10px"}),
                    dcc.Input(
                        id="budget-chart-input",
                        placeholder="Enter Date...",
                        type="string",
                        style={"marginRight": "10px"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center"},
                className="row",
            ),
            html.Div(
                [
                    # budget chart
                    html.Button("Budget Chart", id="budget-chart-button", n_clicks=0),
                    dcc.Graph(
                        id="budget-chart",
                    ),
                    html.Div(id="budget-chart-labels", children=""),
                    # income chart
                    html.Button("Income Chart", id="income-chart-button", n_clicks=0),
                    dcc.Graph(
                        id="income-chart",
                    ),
                    # compare chart
                    html.Button(
                        "Compare Chart", id="budget-compare-button", n_clicks=0
                    ),
                    dcc.Graph(
                        id="compare-chart",
                    ),
                ],
                className="row",
            ),
        ]
    )
