"""Plaid Link page."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, clientside_callback, dcc, html
from flask import jsonify, request
from flask_login import current_user

from folioflex.integrations import plaid
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/plaid_link", title="folioflex - Simple Test")

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Create layout for the Plaid dashboard."""
    return html.Div(
        [
            dcc.Store(id="plaid-token", storage_type="memory"),
            dbc.Button("Open Plaid", id="plaid-button", color="primary"),
            # Add a div for the Plaid handler
            html.Div(id="plaid-handler-div"),
        ]
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/
#


@callback(
    Output("plaid-token", "data"),
    Input("plaid-button", "n_clicks"),
    prevent_initial_call=True,
)
def get_link_token(n_clicks):
    """Get Plaid Link token."""
    if not n_clicks:
        return dash.no_update

    # username = current_user.get_id()
    username = "test"

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
                        body: JSON.stringify({ public_token: public_token })
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
    webhook_code = webhook_data.get("webhook_code")
    plaid_item_id = webhook_data.get("item_id")
    response = plaid.server.handle_plaid_webhooks(webhook_data)

    logger.info(f"{webhook_code}: {plaid_item_id} - {response}")

    return jsonify({"status": "success"}), 200


@dash.get_app().server.route("/plaid-exchange-token", methods=["POST"])
def exchange_token():
    """Exchange public token for access token."""
    if not request.is_json:
        return jsonify({"error": "Content type must be application/json"}), 400

    token_data = request.get_json()
    public_token = token_data.get("public_token")

    if not public_token:
        logger.error("No public token provided")
        return jsonify({"error": "No public token provided"}), 400

    response = plaid.server.exchange_public_token(public_token=public_token)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        logger.error(f"Failed to exchange public token: {response.text}")
        return jsonify({"error": "Failed to exchange token"}), response.status_code
