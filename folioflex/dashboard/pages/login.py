"""Login dashboard."""

import dash
from dash import Input, Output, State, callback, dcc, html

from folioflex.dashboard.utils import dashboard_helper
from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/", title="folioflex - Stocks", order=0)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


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


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# User credentials
# dictionary of username and password
# e.g. {"username": "password"}
credentials = {config_helper.FFX_USERNAME: config_helper.FFX_PASSWORD}


@callback(
    [
        Output("login-status", "data"),
        Output("login-alert", "children"),
    ],
    Input("login-button", "n_clicks"),
    [State("username", "value"), State("password", "value")],
    prevent_initial_call=True,
)
def validate_login(n_clicks, username, password):
    """Validate login credentials."""
    if not n_clicks:
        # Return empty values if the button has not been clicked yet
        return (
            dash.no_update,
            dash.no_update,
        )
    elif (
        username is not None
        and password is not None
        and (username, password) in credentials.items()
    ):
        return (
            {"logged_in": True},
            "Success (switch pages to see the change)",
        )
    else:
        return (
            {"logged_in": False},
            "Invalid Credentials",
        )
