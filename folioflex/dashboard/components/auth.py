"""Authorization component."""

import os

import dash
from dash import Input, Output, callback
from flask import Flask, redirect, request, session
from flask_login import LoginManager, UserMixin, current_user, login_user

from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)

#   _                _
#  | |    ___   __ _(_)_ __
#  | |   / _ \ / _` | | '_ \
#  | |__| (_) | (_| | | | | |
#  |_____\___/ \__, |_|_| |_|
#              |___/

# server setup
server = Flask(__name__)

# login parameters
restricted_page = {"/budget": True, "/personal": True, "/plaid": True}
VALID_USERNAME_PASSWORDS = config_helper.USERNAME_PASSWORDS

# login information
server.config.update(SECRET_KEY=os.urandom(24))
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"


class User(UserMixin):
    """User class for flask login."""

    def __init__(self, username):
        self.id = username


@login_manager.user_loader
def load_user(username):
    """Reload the user object from the user ID stored in the session."""
    return User(username)


@server.route("/login", methods=["POST"])
def login_button_click():
    """Login button click event."""
    username = request.form["username"]
    password = request.form["password"]
    if VALID_USERNAME_PASSWORDS.get(username) == password:
        login_user(User(username))
        # redirect to page user was trying to access when logged in
        url = session.get("url")
        if url:
            session["url"] = None
            return redirect(url)
        return redirect("/")
    return redirect("/login?error=invalid")


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


@callback(
    Output("url", "pathname"),
    Input("url", "pathname"),
)
def verify_login(path):
    """Update the authentication status header."""
    if path in restricted_page and not current_user.is_authenticated:
        session["url"] = path
        return "/login"
    else:
        return dash.no_update
