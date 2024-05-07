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
from dash import dcc, html
from dash.dependencies import Input, Output

from folioflex.utils import custom_logger

#      _    ____  ____
#     / \  |  _ \|  _ \
#    / _ \ | |_) | |_) |
#   / ___ \|  __/|  __/
#  /_/   \_\_|   |_|

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"],
)
server = app.server
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
        dcc.Store(id="login-status", storage_type="session"),
        html.Div(id="login-alert", children="", style={"display": "none"}),
        navbar,
        dash.page_container,
    ]
)


#  __        _____  ____  _  _______ ____
#  \ \      / / _ \|  _ \| |/ / ____|  _ \
#   \ \ /\ / / | | | |_) | ' /|  _| | |_) |
#    \ V  V /| |_| |  _ <| . \| |___|  _ <
#     \_/\_/  \___/|_| \_\_|\_\_____|_| \_\


@app.callback(
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


if __name__ == "__main__":
    custom_logger.set_log_level("DEBUG", module_prefix="pages")
    app.run_server(debug=True)
