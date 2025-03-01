"""Dashboard logout."""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask_login import current_user, logout_user

dash.register_page(__name__)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Create layout for the logout page."""
    if current_user.is_authenticated:
        logout_user()
    return html.Div(
        [
            # Hidden stores that will be cleared
            dcc.Store(id="transactions-store", storage_type="session", clear_data=True),
            dcc.Store(id="accounts-store", storage_type="session", clear_data=True),
            dbc.Container(
                dbc.Row(
                    dbc.Col(
                        dbc.Card(
                            className="shadow-lg p-4",
                            children=[
                                html.H3(
                                    "Successfully Logged Out",
                                    className="text-center mb-4",
                                ),
                                dbc.Button(
                                    "Return to Login",
                                    href="/login",
                                    color="primary",
                                    className="mx-auto d-block",
                                ),
                            ],
                        ),
                        width={"size": "auto"},
                        className="d-flex justify-content-center",
                    ),
                    className="align-items-center min-vh-100",
                    justify="center",
                ),
                fluid=True,
                className="bg-light",
            ),
        ]
    )
