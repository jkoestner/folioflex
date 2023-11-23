"""Tracker dashboard."""

from dash import dash_table, dcc, html

from folioflex.dashboard import dashboard_helper


def layout(login_status, login_alert):
    """Tracker layout."""
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
                    # initializing the portfolio
                    html.P(),
                    html.Button("Portfolio", id="tracker-initialize", n_clicks=0),
                    # graph
                    html.P(),
                    dcc.Dropdown(
                        id="tracker-dropdown",
                        options=["view_return", "view_market_value"],
                        value="view_return",
                    ),
                    html.P(),
                    html.Div(id="tracker_refresh_text", children=""),
                    html.P(),
                    dcc.Graph(
                        id="tracker-graph",
                    ),
                    html.P(),
                    # creating table for performance
                    html.Label("Performance Table"),
                    dash_table.DataTable(
                        id="tracker_perfomance_table",
                        sort_action="native",
                        page_action="native",
                    ),
                    html.P(),
                    html.P(),
                    # creating table for transactions
                    html.Label("Transactions Table"),
                    dash_table.DataTable(
                        id="tracker_transaction_table",
                        sort_action="native",
                    ),
                ],
                className="row",
            ),
        ]
    )
