"""Login dashboard."""

from dash import dcc, html

from folioflex.dashboard import dashboard_helper


def layout(login_status, login_alert):
    """Login layout."""
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            dcc.Store(id="login-status", data=login_status),
            # ---------------------------------------------------------------
            dashboard_helper.get_menu(),
            dcc.Input(id="username", type="text", placeholder="Enter username"),
            dcc.Input(id="password", type="password", placeholder="Enter password"),
            html.Button("Login", id="login-button"),
            html.Div(id="login-alert", children=login_alert),
        ]
    )
