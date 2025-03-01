"""
Dashboard login.

inspired by:
https://community.plotly.com/t/dash-app-pages-with-flask-login-flow-using-flask/69507
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, html

dash.register_page(__name__)

# Login screen
layout = html.Div(
    className="d-flex justify-content-center align-items-center vh-100 bg-light",
    children=[
        dbc.Card(
            className="shadow-lg p-4",
            children=[
                html.H3("Login", className="text-center mb-4"),
                html.Form(
                    [
                        dbc.Input(
                            placeholder="Username",
                            type="text",
                            id="uname-box",
                            name="username",
                            className="mb-3",
                        ),
                        dbc.Input(
                            placeholder="Password",
                            type="password",
                            id="pwd-box",
                            name="password",
                            className="mb-3",
                        ),
                        dbc.Button(
                            "Login",
                            id="login-button",
                            type="submit",
                            color="primary",
                            className="w-100",
                        ),
                    ],
                    action="/login",
                    method="post",
                ),
                html.Div(id="output-state", className="text-danger mt-3 text-center"),
            ],
            style={"width": "22rem"},
        )
    ],
)

#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


@callback(
    Output("output-state", "children"),
    Input("url", "search"),
)
def update_error_message(search):
    """Display error message if login failed."""
    if search and "error=invalid" in search:
        return "Invalid username or password"
    return ""
