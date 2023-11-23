"""Sector dashboard."""

from dash import dcc, html

from folioflex.dashboard import dashboard_helper


def layout(login_status, login_alert):
    """Sectors layout."""
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
                    html.Button(
                        "Sector initialize", id="sector-initialize", n_clicks=0
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
                    html.Button(
                        "Heatmap initialize", id="heatmap-initialize", n_clicks=0
                    ),
                    dcc.Graph(
                        id="Heatmap-Graph",
                    ),
                ],
                className="row",
            ),
        ]
    )
