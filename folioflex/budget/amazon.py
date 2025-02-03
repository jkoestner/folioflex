"""Update transactions with Amazon descriptions."""

import re
from typing import TYPE_CHECKING, Any, List, Optional

import pandas as pd
from seleniumbase import SB

from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)


def extract_page_data(sb: SB) -> pd.DataFrame:
    """
    Extract data from the page.

    Parameters
    ----------
    sb : seleniumbase.SB
        The driver to use to extract the data.

    Returns
    -------
    order_data : pandas.DataFrame
        The order data extracted from the page, including:
          - date
          - order_id
          - amount
          - payment_method

    """
    # selectors for data
    date_selector = ".apx-transaction-date-container span"
    order_selector = "a.a-link-normal[href*='orderID']"
    amount_selector = ".a-size-base-plus.a-text-bold"
    payment_selector = (
        ".apx-transactions-line-item-component-container ."
        "a-row:first-child .a-size-base.a-text-bold"
    )

    # find the data and create a dict
    dates = sb.find_elements(date_selector)
    orders = sb.find_elements(order_selector)
    amounts = sb.find_elements(amount_selector)
    payment_methods = sb.find_elements(payment_selector)

    order_dict = {"date": [], "order_id": [], "amount": [], "payment_method": []}

    # loop through the data
    for date, order, amount, payment in zip(
        dates, orders, amounts, payment_methods, strict=False
    ):
        order_id = order.text.split("#")[1] if "#" in order.text else order.text
        amount_text = amount.text.strip()
        payment_text = payment.text.strip()

        # only process if it's an order (not a refund)
        if "Order" in order.text:
            order_dict["date"].append(date.text)
            order_dict["order_id"].append(order_id)
            order_dict["amount"].append(amount_text)
            order_dict["payment_method"].append(payment_text)

    # create a df
    order_df = pd.DataFrame(order_dict)
    order_df["date"] = pd.to_datetime(order_df["date"])
    order_df["amount"] = (
        order_df["amount"].str.replace("$", "").str.replace(",", "").astype(float)
    )
    order_df = order_df.sort_values("date", ascending=False)

    return order_df


def has_next_page(sb: SB) -> bool:
    """
    Check if there's a next page button that's not disabled.

    Parameters
    ----------
    sb : seleniumbase.SB
        The driver to use to extract the data.

    Returns
    -------
    has_next_page : bool
        True if there's a next page button that's not disabled

    """
    try:
        # check next page button
        sb.find_element(
            "div.a-column.a-span2.a-text-center.a-span-last .a-button:not(.a-"
            "button-disabled) input.a-button-input"
        )
        return True
    except:
        return False
