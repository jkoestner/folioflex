"""Plaid dashboard."""

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, clientside_callback, dcc, html
from flask import jsonify, request
from flask_login import current_user

from folioflex.dashboard.components import dash_formats
from folioflex.dashboard.utils import dashboard_helper
from folioflex.integrations import plaid
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/plaid", title="folioflex - Plaid", order=6)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/

engine = plaid.database.Engine(config_path="config.yml")


def layout():
    """Create layout for the Plaid dashboard."""
    if not current_user.is_authenticated:
        return html.Div(["Please ", dcc.Link("login", href="/login"), " to continue"])
    return dbc.Container(
        [
            # stores
            dcc.Store(
                id="transactions-store",
                storage_type="session",
            ),
            dcc.Store(
                id="accounts-store",
                storage_type="session",
            ),
            dcc.Store(id="plaid-token", storage_type="memory"),
            # Hidden defaults needed for callbacks
            *dashboard_helper.get_defaults(),
            html.Div(id="plaid-handler-div"),
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
                            dbc.Button(
                                "Add New Account",
                                id="plaid-button",
                                color="primary",
                                className="mb-3 mt-2 d-flex justify-content-end",
                            ),
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
    State("transactions-store", "data"),
    State("accounts-store", "data"),
    State("url", "pathname"),
    prevent_initial_call=False,
)
def update_data(n_clicks, stored_tx_data, stored_accounts_data, pathname):
    """Update both transactions and accounts tables."""
    if n_clicks is None:
        return [dash.no_update] * 7

    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    user_id = engine.get_user_id(username=current_user.get_id())

    # initial load or refresh
    if triggered_id == "refresh-button" or (
        n_clicks is None and (stored_tx_data is None or stored_accounts_data is None)
    ):
        # get transactions
        tx_df = engine.get_user_transactions(user_id)

        # get accounts
        accounts_df = engine.get_user_accounts(user_id)

    # else use stored data
    else:
        tx_df = pd.DataFrame(stored_tx_data)
        accounts_df = pd.DataFrame(stored_accounts_data)

    if tx_df.empty or accounts_df.empty:
        logger.warning(f"user `{user_id}` has no transactions or accounts")
        return [dash.no_update] * 7

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


#   ____  _       _     _   _     _       _
#  |  _ \| | __ _(_) __| | | |   (_)_ __ | | __
#  | |_) | |/ _` | |/ _` | | |   | | '_ \| |/ /
#  |  __/| | (_| | | (_| | | |___| | | | |   <
#  |_|   |_|\__,_|_|\__,_| |_____|_|_| |_|_|\_\


@callback(
    Output("plaid-token", "data"),
    Input("plaid-button", "n_clicks"),
    prevent_initial_call=True,
)
def get_link_token(n_clicks):
    """Get Plaid Link token."""
    if not n_clicks:
        return dash.no_update

    username = current_user.get_id()

    response = plaid.server.create_link_token(username=username)
    if response.status_code == 200:
        return response.json()["link_token"]
    else:
        logger.warning(f"Failed to get link token with user `{username}`")
        return dash.no_update
    return dash.no_update


# clientside backend to use javascript to handle plaid-link
# html.script and callback did not work from my experience
clientside_callback(
    """
    function(token) {
        if (!token) return;

        // Function to initialize Plaid
        function initializePlaid() {
            console.log("Initializing Plaid with token:", token);
            const handler = window.Plaid.create({
                token: token,
                onSuccess: function(public_token, metadata) {
                    console.log("Success:", public_token, metadata);
                    fetch("/plaid-exchange-token", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            public_token: public_token,
                            metadata: metadata
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log("Bank linked successfully", data);
                    })
                    .catch(error => console.error("Error sending token:", error));
                },
                onExit: function(err, metadata) {
                    if (err) console.error("Plaid Link error:", err);
                }
            });

            handler.open();
        }

        // Check if Plaid is loaded
        if (window.Plaid) {
            initializePlaid();
        } else {
            // Wait for Plaid to load
            const script = document.createElement('script');
            script.src = "https://cdn.plaid.com/link/v2/stable/link-initialize.js";
            script.onload = initializePlaid;
            document.head.appendChild(script);
        }
        return;
    }
    """,
    Output("plaid-handler-div", "children"),
    Input("plaid-token", "data"),
    prevent_initial_call=True,
)

#   ____             _
#  |  _ \ ___  _   _| |_ ___  ___
#  | |_) / _ \| | | | __/ _ \/ __|
#  |  _ < (_) | |_| | ||  __/\__ \
#  |_| \_\___/ \__,_|\__\___||___/


@dash.get_app().server.route("/plaid-webhook", methods=["POST"])
def receive_plaid_webhook():
    """Receive Plaid webhooks."""
    if not request.is_json:
        return jsonify({"error": "Content type must be application/json"}), 400

    webhook_data = request.get_json()
    response = plaid.server.handle_plaid_webhooks(webhook_data)

    logger.info(response)

    return jsonify({"status": "success"}), 200


@dash.get_app().server.route("/plaid-exchange-token", methods=["POST"])
def exchange_token():
    """Exchange public token for access token."""
    if not request.is_json:
        return jsonify({"error": "Content type must be application/json"}), 400

    token_data = request.get_json()
    public_token = token_data.get("public_token")
    token_metadata = token_data.get("metadata")

    if not public_token:
        logger.error("No public token provided")
        return jsonify({"error": "No public token provided"}), 400

    response = plaid.server.exchange_public_token(public_token=public_token)

    # perform checks
    # check if public token was exchanged
    if response.status_code != 200:
        return jsonify({"error": "Failed to exchange token"}), response.status_code

    exchange_data = response.json()
    access_token = exchange_data.get("access_token")
    user_id = engine.get_user_id(current_user.get_id())

    # check if user already had item
    plaid_item_id = exchange_data.get("item_id")
    check_item = engine.get_item_info(plaid_item_id=plaid_item_id)
    if check_item:
        logger.info(f"User already had item: {plaid_item_id}")
        return jsonify({"error": "User already had item"}), 400

    # add item to database
    try:
        institution_id = token_metadata.get("institution").get("institution_id")
        engine.add_item(
            user_id=user_id,
            item_id=plaid_item_id,
            access_token=access_token,
            institution_id=institution_id,
        )
    except Exception as e:
        logger.error(f"Failed to add Plaid item to database: {e!s}")
        return jsonify({"error": "Failed to add Plaid item"}), 500

    # add accounts to database
    try:
        accounts = plaid.server.get_accounts(access_token=access_token)
        formatted_accounts = plaid.server.format_accounts(accounts=accounts)
        engine.add_accounts(accounts=formatted_accounts)
    except Exception as e:
        logger.error(f"Failed to add Plaid accounts to database: {e!s}")
        return jsonify({"error": "Failed to add Plaid accounts"}), 500

    # sync transactions
    plaid.server.handle_plaid_webhooks(
        webhook_data={
            "webhook_code": "SYNC_UPDATES_AVAILABLE",
            "item_id": plaid_item_id,
        }
    )

    return jsonify(response.json())
