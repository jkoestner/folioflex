"""Stocks dashboard."""

from dash import dash_table, dcc, html

from folioflex.dashboard import dashboard_helper


def layout(login_status, login_alert):
    """Stocks layout."""
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
                    html.Label("Stock Analysis"),
                    html.P(),
                    dcc.Markdown(
                        """
                    A site to review for insider activity.
                    http://www.insiderinsights.com/free
                    """
                    ),
                    html.P(),
                    dcc.Input(
                        id="stock-input", placeholder="Enter Stock...", type="text"
                    ),
                    html.Button("Active Submit", id="active-button", n_clicks=0),
                    html.Button("Stock Submit", id="stock-button", n_clicks=0),
                    html.Button("Quote Submit", id="quote-button", n_clicks=0),
                    html.Button("News Submit", id="news-button", n_clicks=0),
                    html.Button(
                        "Insider Summary Submit",
                        id="insider-summary-button",
                        n_clicks=0,
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating active information
                            html.P(),
                            dash_table.DataTable(
                                id="active-table",
                                page_action="native",
                                sort_action="native",
                            ),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating stock information
                            dash_table.DataTable(
                                id="stock-table",
                                page_action="native",
                            ),
                        ],
                        className="three columns",
                    ),
                    html.Div(
                        [
                            # creating quote information
                            dash_table.DataTable(
                                id="quote-table",
                                page_action="native",
                            ),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating news information
                            html.P(),
                            dash_table.DataTable(
                                id="news-table",
                                page_action="native",
                            ),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating insider summary
                            html.P(),
                            dash_table.DataTable(
                                id="insider-summary-table",
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
