"""Ideas dashboard."""

from dash import dash_table, dcc, html

from folioflex.dashboard import dashboard_helper


def layout(login_status, login_alert):
    """Ideas layout."""
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
                    dcc.Markdown(
                        """
                    Momentum and Value are 2 metrics that determine the viability of investing in the market.
                    **12 mo Moving Average** - current price of market is greater than the 12 month moving average.
                    **12 mo TMOM** - 12 month return is greater than the return of the 10 year treasury bond
                    It's recommended to do 50% of investment in one method and 50% in other
                    """
                    ),
                    html.P(),
                    dcc.Input(
                        id="idea-input", placeholder="Enter Stock...", type="text"
                    ),
                    html.Button("SMA Submit", id="sma-button", n_clicks=0),
                    html.P(),
                    # creating fed fund rate
                    html.A(
                        "10-Year Treasury",
                        href="https://fred.stlouisfed.org/series/DGS10",
                        target="_blank",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # simple moving average
                            dash_table.DataTable(
                                id="sma-table",
                                page_action="native",
                            ),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
        ]
    )
