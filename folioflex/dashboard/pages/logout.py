"""Dashboard logout."""

import dash
from dash import html
from flask_login import current_user, logout_user

dash.register_page(__name__)


def layout():
    """Create layout for the logout page."""
    if current_user.is_authenticated:
        logout_user()
    return html.Div(
        [
            html.Div(html.H4("You have been logged out")),
        ]
    )
