"""Dashboard logout."""

import dash
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
            html.Div(html.H4("You have been logged out")),
        ]
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/
#
