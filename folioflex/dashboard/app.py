"""
Building plotly dashboard.

Builds plotly pages with call backs. There are 2 options the user has for running code.
1. Fly.io build set up
2. Local running

To run locally:
1. cd into root directory
2. run plotly dashboard - `python app.py`

The ascii text is generated using https://patorjk.com/software/taag/
with "standard font"
"""

import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
from flask import Flask, redirect, request, session
from flask_login import LoginManager, UserMixin, current_user, login_user

from folioflex.dashboard.utils.login_handler import restricted_page
from folioflex.utils import config_helper, custom_logger

#      _    ____  ____
#     / \  |  _ \|  _ \
#    / _ \ | |_) | |_) |
#   / ___ \|  __/|  __/
#  /_/   \_\_|   |_|

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

# credentials
server = Flask(__name__)


@server.route("/login", methods=["POST"])
def login_button_click():
    """Login button click event."""
    if request.form:
        username = request.form["username"]
        password = request.form["password"]
        if VALID_USERNAME_PASSWORD.get(username) is None:
            return (
                """invalid username and/or password <a href='/login'>login here</a>"""
            )
        if VALID_USERNAME_PASSWORD.get(username) == password:
            login_user(User(username))
            url = session.get("url")
            print(url)
            if url:
                session["url"] = None
                return redirect(url)
            return redirect("/")
        return """invalid username and/or password <a href='/login'>login here</a>"""


VALID_USERNAME_PASSWORD = {config_helper.FFX_USERNAME: config_helper.FFX_PASSWORD}

# get random secret key
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


# app configs
app = dash.Dash(
    __name__,
    server=server,
    use_pages=True,
    external_stylesheets=[
        dbc_css,
        dbc.themes.FLATLY,
    ],
)
app.config.suppress_callback_exceptions = True
app.title = "FolioFlex"
app._favicon = "folioflex_logo.ico"

# creating the navbar
page_links = [
    dbc.NavItem(dbc.NavLink(page["name"], href=page["relative_path"]))
    for page in dash.page_registry.values()
]

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            src=app.get_asset_url("folioflex_logo.ico"), height="40px"
                        )
                    ),
                    dbc.Col(
                        [
                            dbc.NavbarBrand("folioflex", className="ms-3 fs-3"),
                            dbc.NavLink(
                                html.Img(
                                    src=app.get_asset_url("github-mark-white.png"),
                                    height="20px",
                                ),
                                href="https://github.com/jkoestner/folioflex",
                                target="_blank",
                                className="ms-2",
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                ],
                align="center",
                className="g-0",
            ),
            dbc.Row(
                dbc.Nav(
                    page_links,
                    className="ms-auto",
                    navbar=True,
                ),
                align="center",
            ),
        ],
        fluid=True,
    ),
    color="primary",
    dark=True,
    sticky="top",
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        navbar,
        dash.page_container,
    ]
)


#  __        _____  ____  _  _______ ____
#  \ \      / / _ \|  _ \| |/ / ____|  _ \
#   \ \ /\ / / | | | |_) | ' /|  _| | |_) |
#    \ V  V /| |_| |  _ <| . \| |___|  _ <
#     \_/\_/  \___/|_| \_\_|\_\_____|_| \_\


@callback(
    Output("interval-component", "interval"),
    [
        Input("task-status", "children"),
        Input("task-id", "children"),
        Input("personal-task-status", "children"),
        Input("personal-task-id", "children"),
        Input("manager-task-status", "children"),
        Input("manager-task-id", "children"),
    ],
)
def toggle_interval_speed(
    task_status,
    task_id,
    personal_task_status,
    personal_task_id,
    manager_task_status,
    manager_task_id,
):
    """
    Triggered by changes in task-id and task-status divs.

    It switches the page refresh interval to fast (1 sec) if a task is running,
    or slow (24 hours) if a task is pending or complete.
    """
    if (
        (task_id != "none" and task_status in ["waiting", "PENDING"])
        or (
            personal_task_id != "none"
            and personal_task_status in ["waiting", "PENDING"]
        )
        or (manager_task_id != "none" and manager_task_status in ["waiting", "PENDING"])
    ):
        return 1000
    else:
        return 24 * 60 * 60 * 1000


@app.callback(
    Output("url", "pathname"),
    Input("url", "pathname"),
)
def update_authentication_status(path):
    """Update the authentication status header."""
    if current_user.is_authenticated:
        if path == "/login":
            return "/"
        else:
            return dash.no_update
    elif path in restricted_page:
        print("test")
        session["url"] = path
        return "/login"
    else:
        return dash.no_update


if __name__ == "__main__":
    custom_logger.set_log_level("DEBUG", module_prefix="pages")
    app.run_server(debug=True)
