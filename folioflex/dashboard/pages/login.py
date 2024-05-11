"""
Dashboard login.

inspired by:
https://community.plotly.com/t/dash-app-pages-with-flask-login-flow-using-flask/69507
"""

import dash
from dash import dcc, html

dash.register_page(__name__)

# Login screen
layout = html.Form(
    [
        html.H4("Please log in to continue:", id="h1"),
        dcc.Input(
            placeholder="Enter your username",
            type="text",
            id="uname-box",
            name="username",
        ),
        dcc.Input(
            placeholder="Enter your password",
            type="password",
            id="pwd-box",
            name="password",
        ),
        html.Button(children="Login", n_clicks=0, type="submit", id="login-button"),
        html.Div(children="", id="output-state"),
    ],
    method="POST",
)
