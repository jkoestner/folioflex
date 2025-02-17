"""Plaid dashboard."""

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html
from flask_login import current_user

from folioflex.dashboard.components import dash_formats
from folioflex.dashboard.utils import dashboard_helper
from folioflex.utils import custom_logger, database

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/plaid", title="folioflex - Plaid", order=6)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/

engine = database.Engine(config_path="config.yml")


def layout():
    """Create layout for the Plaid dashboard."""
    if not current_user.is_authenticated:
        return html.Div(["Please ", dcc.Link("login", href="/login"), " to continue"])
    return dbc.Container(
        [
            print(current_user.get_id()),
            # stores
            dcc.Store(
                id="transactions-store",
                storage_type="session",
            ),
            dcc.Store(
                id="accounts-store",
                storage_type="session",
            ),
            # Hidden defaults needed for callbacks
            *dashboard_helper.get_defaults(),
            # Header
            html.H2("Plaid", className="text-center my-4"),
            # Key Metrics
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                "Total Assets",
                                                className="card-title text-success",
                                            ),
                                            html.H2(
                                                id="total-assets",
                                                className="card-text text-success",
                                            ),
                                            html.P(
                                                "Total balance in deposit accounts",
                                                className="card-text text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3 text-center",
                            )
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                "Total Credit",
                                                className="card-title text-danger",
                                            ),
                                            html.H2(
                                                id="total-credit",
                                                className="card-text text-danger",
                                            ),
                                            html.P(
                                                "Total balance in credit accounts",
                                                className="card-text text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3 text-center",
                            )
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                "Net",
                                                className="card-title",
                                            ),
                                            html.H2(
                                                id="net-worth",
                                                className="card-text",
                                            ),
                                            html.P(
                                                "Assets minus Credit",
                                                className="card-text text-muted",
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-3 text-center",
                            )
                        ],
                        width=4,
                    ),
                ],
                className="mb-3",
            ),
            # Transactions Section
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Refresh Data",
                                id="refresh-button",
                                color="primary",
                                className="mb-3 me-2",
                            ),
                            dcc.Dropdown(
                                id="label-filter",
                                options=[{"label": "All", "value": "all"}],
                                value="all",
                                placeholder="Filter by Label",
                                className="mb-3",
                                style={"width": "200px", "display": "inline-block"},
                            ),
                        ],
                        width="auto",
                    ),
                ]
            ),
            # Transactions Table
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-transactions",
                                type="dot",
                                children=html.Div(id="transactions-table"),
                            ),
                            dbc.Toast(
                                "Categories saved successfully!",
                                id="save-success-toast",
                                header="Success",
                                is_open=False,
                                duration=1000,
                                icon="success",
                                style={
                                    "position": "fixed",
                                    "top": 66,
                                    "right": 10,
                                    "width": 350,
                                },
                            ),
                        ]
                    ),
                ],
                className="mb-3",
            ),
            # Accounts Section
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            dcc.Loading(
                                id="loading-accounts",
                                type="dot",
                                children=html.Div(id="accounts-table"),
                            ),
                        ],
                        title="Accounts Overview",
                    ),
                ],
                start_collapsed=True,
            ),
        ]
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/
#


@callback(
    Output("transactions-table", "children"),
    Output("transactions-store", "data"),
    Output("accounts-table", "children"),
    Output("accounts-store", "data"),
    Output("total-assets", "children"),
    Output("total-credit", "children"),
    Output("net-worth", "children"),
    Input("refresh-button", "n_clicks"),
    Input("transactions-store", "data"),
    Input("accounts-store", "data"),
    prevent_initial_call=False,
)
def update_data(n_clicks, stored_tx_data, stored_accounts_data):
    """Update both transactions and accounts tables."""
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    user_id = engine.get_user_id(username=current_user.get_id())
    # initial load or refresh
    if triggered_id == "refresh-button" or (
        n_clicks is None and (stored_tx_data is None or stored_accounts_data is None)
    ):
        logger.info("refreshing transactions")
        # get transactions
        tx_df = engine.get_user_transactions(user_id)

        # get accounts
        accounts_df = engine.get_user_accounts(user_id)

    # else use stored data
    else:
        tx_df = pd.DataFrame(stored_tx_data)
        accounts_df = pd.DataFrame(stored_accounts_data)

    # create grids and stores
    stored_tx_data = tx_df.to_dict("records")
    stored_accounts_data = accounts_df.to_dict("records")
    tx_grid_column_defs = dash_formats.get_column_defs(tx_df, edit=["label"])
    tx_grid_column_defs[1].update({"width": 400})
    tx_grid = dag.AgGrid(
        id="transactions-grid",
        rowData=tx_df.to_dict("records"),
        columnDefs=tx_grid_column_defs,
        defaultColDef={
            "resizable": True,
            "sortable": True,
            "filter": True,
            "floatingFilter": True,
        },
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "editType": "fullRow",
        },
        rowClass="ag-row-striped",
        style={"height": "1000px"},
        className="ag-theme-material",
    )

    accounts_grid = dag.AgGrid(
        id="accounts-grid",
        rowData=accounts_df.to_dict("records"),
        columnDefs=dash_formats.get_column_defs(accounts_df),
        defaultColDef={
            "resizable": True,
            "sortable": True,
            "filter": True,
            "floatingFilter": True,
        },
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 10,
        },
    )

    # create kpis
    total_assets = accounts_df[accounts_df["type"] == "depository"][
        "current_balance"
    ].sum()
    total_credit = accounts_df[accounts_df["type"] == "credit"]["current_balance"].sum()
    net_worth = total_assets - total_credit

    return (
        tx_grid,
        stored_tx_data,
        accounts_grid,
        stored_accounts_data,
        f"${total_assets:,.2f}",
        f"${total_credit:,.2f}",
        f"${net_worth:,.2f}",
    )


@callback(
    Output("save-success-toast", "is_open"),
    Input("transactions-grid", "cellValueChanged"),
    State("transactions-store", "data"),
    prevent_initial_call=True,
)
def save_labels(cell_changed, stored_data):
    """Save updated labels to the database."""
    if cell_changed is None:
        return False

    # get the changed cell data
    changed_row = cell_changed[0]["data"]
    row_id = changed_row["id"]
    row_label = changed_row["label"]
    label_df = pd.DataFrame([{"id": row_id, "label": row_label}])

    try:
        logger.info(f"updated labels for transaction {row_id} to {row_label}")
        engine.bulk_update(
            tx_df=label_df, table_name="transactions_table", where_column="id"
        )
        return True
    except Exception as e:
        logger.error(f"error updating labels: {e!s}")
        return False


@callback(
    Output("transactions-grid", "rowData"),
    Input("label-filter", "value"),
    State("transactions-store", "data"),
)
def filter_transactions(selected_label, stored_data):
    """Filter transactions based on selected label."""
    if not stored_data or selected_label == "all":
        return stored_data

    filtered_data = [
        row
        for row in stored_data
        if (row.get("label") == selected_label)
        or (selected_label == "null" and row.get("label") is None)
    ]
    return filtered_data


@callback(
    Output("label-filter", "options"),
    Input("transactions-store", "data"),
)
def update_label_options(stored_tx_data):
    """Update label filter options based on available labels."""
    if not stored_tx_data:
        return [{"label": "All", "value": "all"}]

    # get unique labels
    tx_df = pd.DataFrame(stored_tx_data)
    labels = tx_df["label"].dropna().unique()

    # create options with null and all
    options = [
        {"label": "all", "value": "all"},
        {"label": "unlabeled", "value": "null"},
    ]

    # Add all other unique labels
    options.extend([{"label": label, "value": label} for label in sorted(labels)])

    return options
