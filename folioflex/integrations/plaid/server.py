"""
Server helper functions for Plaid.

The server gets data from plaid and uses that to update the database.

https://plaid.com/docs/api/

"""

import json
from typing import Optional

import pandas as pd
import requests

from folioflex.integrations.plaid import database
from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)

headers = {
    "Content-type": "application/json",
}
plaid_env = config_helper.PLAID_ENV


def handle_plaid_webhooks(webhook_data: dict) -> dict:
    """
    Handle Plaid webhook data.

    Will receive the webhook and then update the database accordingly.

    webhooks that are handled
    - SYNC_UPDATES_AVAILABLE

    plaid webhooks
    - https://plaid.com/docs/api/items/#webhooks
    - https://plaid.com/docs/api/products/transactions/#webhooks

    Parameters
    ----------
    webhook_data : dict
        The data from the Plaid webhook.

    Returns
    -------
    response : string
        The response from the webhook.

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
        # update transactions
        transactions = transactions_sync(access_token, cursor)
        added = format_transactions(transactions.get("added"))
        modified = format_transactions(transactions.get("modified"))
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
        # update accounts
        accounts = get_accounts(access_token=access_token)
        formatted_accounts = format_accounts(accounts=accounts)
        engine.add_accounts(accounts=formatted_accounts)
        response = f"{webhook_code}: {plaid_item_id} - {updated_data}"
    elif webhook_code == "TRANSACTIONS_REMOVED":
        # delete transactions
        removed_transactions = webhook_data.get("removed_transactions")
        engine.delete_transactions(removed_transactions)
        response = f"{webhook_code}: removed {len(removed_transactions)} transactions"
    elif webhook_code == "WEBHOOK_UPDATE_ACKNOWLEDGED":
        response = f"{webhook_code}: {plaid_item_id}"
    elif webhook_code == "DEFAULT_UPDATE":
        response = f"{webhook_code}: using transactions_sync instead"
    else:
        response = f"{webhook_code}: webhook not handled"

    return response


def handle_plaid_maintenance(user_data: dict) -> None:
    """
    Handle plaid maintenance.

    The maintenance codes that are handled are:
    - {"maintenance_code": "DELETE_ITEM", "details": {"access_token": "string"}}

    Parameters
    ----------
    user_data : dict
        The user data.

    Returns
    -------
    None

    """
    # get the user data
    maintenance_code = user_data.get("maintenance_code")
    details = user_data.get("details")

    # connect to database
    engine = database.Engine(config_path="config.yml")

    # process user_data codes
    if maintenance_code == "DELETE_ITEM":
        item_info = get_item_info(access_token=details["access_token"])
        if item_info.get("item") is None:
            logger.warning(f"{item_info.get("error_code")}")
            return
        logger.info("Deleting item")

        # get the ids to delete
        plaid_item_id = item_info["item"]["item_id"]
        item_id = engine.get_item_info(plaid_item_id=plaid_item_id)["id"]

        accounts_df = engine.get_item_accounts(item_id=item_id)
        plaid_account_ids = accounts_df.get(
            "plaid_account_id", pd.Series(dtype=object)
        ).tolist()

        transactions_df = engine.get_item_transactions(item_id=item_id)
        plaid_transaction_ids = transactions_df.get(
            "plaid_transaction_id", pd.Series(dtype=object)
        ).tolist()

        # delete the item
        engine.delete_transactions(plaid_transaction_ids)
        engine.delete_accounts(plaid_account_ids)
        engine.delete_item(plaid_item_id)
        remove_item(access_token=details["access_token"])


def create_link_token(
    username: str, webhook: Optional[str] = None, redirect_uri: Optional[str] = None
) -> dict:
    """
    Create a link token for a user.

    https://plaid.com/docs/api/link/#linktokencreate

    Parameters
    ----------
    username : str
        The username for the request.
    webhook : str, optional
        The webhook for the request.
    redirect_uri : str, optional
        The redirect uri for the request.

    Returns
    -------
    response : json
        The link token for the user.

    """
    logger.info(f"Creating link token for user: `{username}`")
    if not webhook:
        webhook = config_helper.PLAID_WEBHOOK
    if not redirect_uri:
        redirect_uri = config_helper.PLAID_REDIRECT_URI
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "client_name": "FolioFlex",
        "language": "en",
        "country_codes": ["US"],
        "user": {"client_user_id": username},
        "products": ["transactions"],
        "redirect_uri": redirect_uri,
        "webhook": webhook,
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/link/token/create",
        headers=headers,
        data=json.dumps(data),
    )

    return response


def exchange_public_token(public_token: str) -> dict:
    """
    Exchange a public token for an access token.

    https://plaid.com/docs/api/items/#itempublic_tokenexchange

    Parameters
    ----------
    public_token : str
        The public token for the request.

    Returns
    -------
    response : json
        The access token for the public token.

    """
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "public_token": public_token,
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/item/public_token/exchange",
        headers=headers,
        data=json.dumps(data),
    )

    if response.status_code != 200:
        logger.error(f"Failed to exchange public token: {response.text}")

    logger.info("Exchanged public token")

    return response


def transactions_sync(access_token: str, cursor: Optional[str] = None) -> dict:
    """
    Fetch transactions for an item from the last known cursor.

    This method is preferred over the `transactions_get` method as it is
    more efficient. It handles pagination automatically by checking the 'has_more'
    flag and using the 'next_cursor' value until all transactions are retrieved.

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
    logger.info(f"Fetching transactions for access token: `{access_token}`")

    # initialize dictionary
    transactions = {
        "accounts": [],
        "added": [],
        "modified": [],
        "removed": [],
        "next_cursor": cursor,
        "has_more": True,  # start with True to enter the loop
        "request_id": None,
        "transactions_update_status": None,
    }

    # loop through the transactions
    while transactions["has_more"]:
        data = {
            "client_id": config_helper.PLAID_CLIENT_ID,
            "secret": config_helper.PLAID_SECRET,
            "access_token": access_token,
            "cursor": transactions["next_cursor"],
            "count": 250,
        }
        response = requests.post(
            f"https://{plaid_env}.plaid.com/transactions/sync",
            headers=headers,
            data=json.dumps(data),
        )
        transactions_iteration = response.json()

        # append new transaction data to our result
        if transactions_iteration.get("accounts"):
            transactions["accounts"] = transactions_iteration["accounts"]
        if transactions_iteration.get("added"):
            transactions["added"].extend(transactions_iteration["added"])
        if transactions_iteration.get("modified"):
            transactions["modified"].extend(transactions_iteration["modified"])
        if transactions_iteration.get("removed"):
            transactions["removed"].extend(transactions_iteration["removed"])
        transactions["next_cursor"] = transactions_iteration.get("next_cursor")
        transactions["has_more"] = transactions_iteration.get("has_more", False)
        transactions["request_id"] = transactions_iteration.get("request_id")
        transactions["transactions_update_status"] = transactions_iteration.get(
            "transactions_update_status"
        )

    return transactions


def format_accounts(accounts: dict) -> list:
    """
    Format accounts for the database.

    Parameters
    ----------
    accounts : list
        The accounts to format.

    Returns
    -------
    accounts_formated : list
        The formatted accounts.

    """
    item_id = accounts["item"]["item_id"]
    formatted_accounts = [
        {
            "item_id": item_id,
            "plaid_account_id": account["account_id"],
            "name": account["name"],
            "mask": account["mask"],
            "official_name": account["official_name"],
            "current_balance": account["balances"]["current"],
            "available_balance": account["balances"]["available"],
            "iso_currency_code": account["balances"]["iso_currency_code"],
            "unofficial_currency_code": account["balances"]["unofficial_currency_code"],
            "type": account["type"],
            "subtype": account["subtype"],
        }
        for account in accounts["accounts"]
    ]
    return formatted_accounts


def format_transactions(transactions):
    """
    Format transactions for the database.

    Parameters
    ----------
    transactions : list
        The transactions to format.

    Returns
    -------
    formatted : list
        The formatted transactions.

    """
    formatted = []
    for tx in transactions:
        # coerce None -> empty list
        cats = tx.get("category") or []
        formatted.append(
            {
                "account_id": tx["account_id"],
                "plaid_transaction_id": tx["transaction_id"],
                "plaid_category_id": tx["category_id"],
                "category": cats[0] if len(cats) >= 1 else None,
                "subcategory": cats[1] if len(cats) >= 2 else None,
                "type": tx["transaction_type"],
                "name": tx["name"],
                "amount": tx["amount"],
                "iso_currency_code": tx["iso_currency_code"],
                "unofficial_currency_code": tx["unofficial_currency_code"],
                "date": tx["date"],
                "pending": tx["pending"],
                # personal_finance_category is always an object (never null)
                "primary_category": tx["personal_finance_category"]["primary"],
                "detailed_category": tx["personal_finance_category"]["detailed"],
                "confidence_level": tx["personal_finance_category"]["confidence_level"],
                "account_owner": tx.get("account_owner"),  # could be None
            }
        )
    return formatted


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
    logger.debug(f"Getting item info for access token: `{access_token}`")
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/item/get",
        headers=headers,
        data=json.dumps(data),
    )
    item = response.json()
    return item


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
    logger.info(f"Getting accounts for access token: `{access_token}`")
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/accounts/get",
        headers=headers,
        data=json.dumps(data),
    )
    accounts = response.json()

    return accounts


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
    logger.info(f"Getting institution info for institution id: `{institution_id}`")
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "institution_id": institution_id,
        "country_codes": ["US"],
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/institutions/get_by_id",
        headers=headers,
        data=json.dumps(data),
    )
    institution = response.json()

    return institution


def update_item_webhook(access_token: str, webhook: str) -> dict:
    """
    Update an item's webhook.

    https://plaid.com/docs/api/items/#itemwebhookupdate

    Parameters
    ----------
    access_token : str
        The access token for the item.
    webhook : str
        The webhook url for the item.

    Returns
    -------
    item : dict
        The item for the access token.

    """
    logger.info(
        f"Updating webhook for access token: `{access_token}` \n"
        f"webhook: `{webhook}`"
    )
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
        "webhook": webhook,
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/item/webhook/update",
        headers=headers,
        data=json.dumps(data),
    )
    item = response.json()
    return item


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
    logger.info(f"Removing item from serverfor access token: `{access_token}`")
    data = {
        "client_id": config_helper.PLAID_CLIENT_ID,
        "secret": config_helper.PLAID_SECRET,
        "access_token": access_token,
    }
    response = requests.post(
        f"https://{plaid_env}.plaid.com/item/remove",
        headers=headers,
        data=json.dumps(data),
    )
    request = response.json()

    return request
