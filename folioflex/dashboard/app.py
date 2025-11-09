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

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
from flask_login import current_user

from folioflex.dashboard.components import auth
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

#      _    ____  ____
#     / \  |  _ \|  _ \
#    / _ \ | |_) | |_) |
#   / ___ \|  __/|  __/
#  /_/   \_\_|   |_|

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
server = auth.server

# app configs
app = dash.Dash(
    __name__,
    server=server,
    use_pages=True,
    external_stylesheets=[
        dbc_css,
        dbc.themes.SANDSTONE,
    ],
)
app.config.suppress_callback_exceptions = True
app.title = "FolioFlex"
app._favicon = "folioflex_logo.ico"

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="manifest" href="/assets/manifest.json">
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# creating the navbar
page_links = [
    dbc.NavItem(dbc.NavLink(page["name"], href=page["relative_path"]))
    for page in dash.page_registry.values()
    if page["name"] not in ["Login", "Logout"]
]

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            src=app.get_asset_url("folioflex_logo.png"), height="40px"
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
            dbc.Nav(page_links, navbar=True, className="ms-auto"),
            dbc.Nav(
                [
                    html.Div(id="user-auth-status"),
                ],
                navbar=True,
            ),
        ],
        fluid=True,
    ),
    color="primary",
    dark=True,
)

app.layout = html.Div(
    [
        html.Link(rel="shortcut icon", href="/assets/folioflex.png"),
        dcc.Location(id="url", refresh=True),
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


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


@callback(
    Output("user-auth-status", "children"),
    Input("url", "pathname"),
)
def update_auth_status(pathname):
    """Update the authentication status in the navbar."""
    try:
        if current_user.is_authenticated:
            return [
                dbc.NavItem(
                    [
                        html.A(
                            f"Logout ({current_user.id})",
                            href="/logout",
                            className="nav-link me-2",
                        ),
                    ]
                )
            ]
        else:
            return [dbc.NavItem(dbc.NavLink("Login", href="/login", className="me-2"))]
    except Exception as e:
        logger.error(f"Error in update_auth_status: {e}")
        return []


if __name__ == "__main__":
    custom_logger.set_log_level("DEBUG", module_prefix="pages")
    app.run(debug=True, host="0.0.0.0")
