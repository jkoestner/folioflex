"""
Server helper functions for Plaid.

The server gets data from plaid and uses that to update the database.

https://plaid.com/docs/api/

"""

import json
from typing import Optional

import requests

from folioflex.utils import config_helper, custom_logger, database

logger = custom_logger.setup_logging(__name__)

headers = {
    "Content-type": "application/json",
}


def handle_plaid_webhooks(webhook_data: dict) -> dict:
    """
    Handle Plaid webhook data.

    Will receive the webhook and then update the database accordingly.

    Parameters
    ----------
    webhook_data : dict
        The data from the Plaid webhook.

    Returns
    -------
    dict
        The updated data containing counts of added,
        modified, and removed transactions.

    """
    # initialize dict
    updated_data = {"added": [], "modified": [], "removed": []}

    # get the webhook data
    webhook_code = webhook_data.get("webhook_code")
    plaid_item_id = webhook_data.get("item_id")

    # connect to database to get the item info to process
    engine = database.Engine(config_path="config.yml")
    item_info = engine.get_item_info(plaid_item_id)
    access_token = item_info.get("plaid_access_token")
    cursor = item_info.get("transactions_cursor")

    # update database with new transactions and cursor if available
    if webhook_code == "SYNC_UPDATES_AVAILABLE":
        transactions = transactions_sync(access_token, cursor)
        added = transactions.get("added")
        modified = transactions.get("modified")
        removed = transactions.get("removed")
        new_cursor = transactions.get("next_cursor")
        if added:
            engine.add_transactions(added)
        if modified:
            engine.add_transactions(modified)
        if removed:
            removed_ids = [tx.get("transaction_id") for tx in removed]
            engine.delete_transactions(removed_ids)
        if new_cursor != cursor:
            engine.update_item_cursor(plaid_item_id, new_cursor)
        updated_data = {
            "added": len(added),
            "modified": len(modified),
            "removed": len(removed),
        }

    return updated_data


def transactions_sync(access_token: str, cursor: Optional[str] = None) -> dict:
    """
    Fetch transactions for an item from the last known cursor.

    This method is preferred over the `transactions_get` method as it is
    more efficient.

    https://plaid.com/docs/api/products/transactions/#transactionssync

    Parameters
    ----------
    access_token : str
        The access token for the item.
    cursor : str
        The cursor for the item.

    Returns
    -------
    transactions : list
        The transactions for the item.

    """
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
        "cursor": cursor,
        "count": 250,
    }
    response = requests.post(
        "https://production.plaid.com/transactions/sync",
        headers=headers,
        data=json.dumps(data),
    )
    transactions = response.json()

    return transactions


def get_accounts(access_token: str) -> dict:
    """
    Get the accounts for an item.

    https://plaid.com/docs/api/items/#accountsget

    Parameters
    ----------
    access_token : str
        The access token for the item.

    Returns
    -------
    accounts : list
        The accounts for the item.

    """
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
    }
    response = requests.post(
        "https://production.plaid.com/accounts/get",
        headers=headers,
        data=json.dumps(data),
    )
    accounts = response.json()

    return accounts


def get_item_info(access_token: str) -> dict:
    """
    Get information about an item.

    https://plaid.com/docs/api/items/#itemget

    Parameters
    ----------
    access_token : str
        The access token for the item.

    Returns
    -------
    item : dict
        The item for the access token.

    """
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
    }
    response = requests.post(
        "https://production.plaid.com/item/get",
        headers=headers,
        data=json.dumps(data),
    )
    item = response.json()
    return item


def get_institution_info(institution_id: str) -> dict:
    """
    Get information about an institution.

    https://plaid.com/docs/api/institutions/#institutionsget_by_id

    Parameters
    ----------
    institution_id : str
        The institution id for the request.

    Returns
    -------
    institution : dict
        The institution for the id.

    """
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "institution_id": institution_id,
        "country_codes": ["US"],
    }
    response = requests.post(
        "https://production.plaid.com/institutions/get_by_id",
        headers=headers,
        data=json.dumps(data),
    )
    institution = response.json()

    return institution


def remove_item(access_token: str) -> dict:
    """
    Remove an item from Plaid.

    https://plaid.com/docs/api/items/#itemremove

    Parameters
    ----------
    access_token : str
        The access token for the item.

    Returns
    -------
    request : dict
        The request for the item.

    """
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
    }
    response = requests.post(
        "https://production.plaid.com/item/remove",
        headers=headers,
        data=json.dumps(data),
    )
    request = response.json()

    return request
