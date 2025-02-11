"""Update transactions with Amazon descriptions."""

import re
import time
from datetime import datetime
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup as bs
from seleniumbase import SB

from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)


def get_amazon_tx(
    user_data_dir: str, max_pages: int = 1, login: Optional[bool] = False, **kwargs
):
    """
    Get transactions from Amazon.

    The transaction of date, amount and items are from website
      - https://www.amazon.com/gp/css/order-history

    Parameters
    ----------
    user_data_dir : str
        The path to the user data dir for the browser
    max_pages : int (optional)
        The number of pages to get
    login : bool (optional)
        Whether to login to the website
    **kwargs : dict (optional)
        Keyword arguments for the driver

    Returns
    -------
    amazon_tx : pd.DataFrame
        The transactions from Amazon

    """
    # initialize parameters
    current_page = 1
    page_list = []
    timeout = 5

    # loop through website data to get date paid and amount
    # with SB there are a few best practices:
    #  - use UC for remaining undetected
    #  - use a user_data_dir to store cookies and other user data
    #  - use a binary_location to specify the browser
    #  - use a proxy to avoid fingerprint detection
    #  - uc_click is really only for detection buttons
    logger.info("Getting orders from website")
    with SB(
        uc=True,
        user_data_dir=user_data_dir,
        **kwargs,
    ) as sb:
        sb.uc_open_with_reconnect(
            "https://www.amazon.com/gp/css/order-history",
        )
        if login:
            logger.info("login within 30 seconds.")
            sb.reconnect(timeout=30)
        try:
            sb.assert_text("Your Orders", timeout=timeout)
        except Exception:
            logger.warning("there is a captcha here and must login within 30 seconds.")
            sb.reconnect(timeout=30)
            logger.info("reconnected")
        logger.info(f"getting data for `{max_pages}` max_pages")
        while current_page <= max_pages:
            next_page = 'a:contains("→")'
            page_data = extract_page_data(sb)
            page_list.append(page_data)
            current_page += 1
            if not sb.is_element_clickable(next_page) or current_page > max_pages:
                break
            sb.click(next_page)
            time.sleep(2)
            sb.wait_for_element(next_page)
    logger.info(f"reached last page: `{current_page-1}`")
    amazon_tx = pd.concat(page_list, ignore_index=True)

    # remove nas
    amazon_tx = amazon_tx.dropna(subset=["date"])

    return amazon_tx


def extract_page_data(sb: SB) -> pd.DataFrame:
    """
    Extract data from the page.

    Parameters
    ----------
    sb : seleniumbase.SB
        The driver to use to extract the data.

    Returns
    -------
    page_data : pandas.DataFrame
        The order data extracted from the page, including:
          - date
          - amount
          - items

    """
    # initialize variables
    soup = bs(sb.get_page_source(), "html.parser")
    order_list = []

    # find all order cards
    order_cards = soup.find_all("div", class_="order-card")

    # loop through the order cards
    for order_card in order_cards:
        order_dict = {}

        try:
            date_text = order_card.find_all(
                "span", class_="a-size-base a-color-secondary aok-break-word"
            )[0].text.strip()
            order_dict["date"] = datetime.strptime(date_text, "%B %d, %Y")
        except Exception:
            order_dict["date"] = None

        try:
            amount_text = order_card.find_all(
                "span", class_="a-size-base a-color-secondary aok-break-word"
            )[1].text.strip()
            order_dict["amount"] = float(re.sub(r"[^\d.]", "", amount_text))
        except Exception:
            order_dict["amount"] = None

        try:
            item_list = []
            items = order_card.find_all("div", class_="yohtmlc-product-title")
            for item in items:
                item_text = " ".join(item.text.strip().split()[:3])
                item_list.append(item_text)
            item_string = "amazon - " + "; ".join(item_list)
            order_dict["product_name"] = item_string
        except Exception:
            order_dict["product_name"] = None

        order_list.append(order_dict)

    page_data = pd.DataFrame(order_list)

    return page_data


def extract_page_data_old(sb: SB) -> pd.DataFrame:
    """
    Extract data from the page.

    Parameters
    ----------
    sb : seleniumbase.SB
        The driver to use to extract the data.

    Returns
    -------
    page_data : pandas.DataFrame
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
    page_data = pd.DataFrame(order_dict)
    page_data["date"] = pd.to_datetime(page_data["date"])
    page_data["amount"] = (
        page_data["amount"].str.replace("$", "").str.replace(",", "").astype(float)
    )
    page_data = page_data.sort_values("date", ascending=False)

    return page_data


def get_amazon_tx_old(
    amazon_dir: str, user_data_dir: str, max_pages: int = 1, **kwargs
):
    """
    Get transactions from Amazon.

    The transaction of date and amount are from website
      - https://www.amazon.com/cpe/yourpayments/transactions
    The descriptions are from a data dump from amazon
      - https://www.amazon.com/hz/privacy-central/data-requests/preview.html
      - requesting your orders

    Parameters
    ----------
    amazon_dir : str
        The path to the amazon data dump
    user_data_dir : str
        The path to the user data dir for the browser
    max_pages : int (optional)
        The number of pages to get
    **kwargs : dict (optional)
        Keyword arguments for the driver

    Returns
    -------
    amazon_tx : pd.DataFrame
        The transactions from Amazon

    """
    # initialize parameters
    current_page = 1
    page_list = []
    timeout = 5

    # loop through website data to get date paid and amount
    # with SB there are a few best practices:
    #  - use UC for remaining undetected
    #  - use a user_data_dir to store cookies and other user data
    #  - use a binary_location to specify the browser
    #  - use a proxy to avoid fingerprint detection
    #  - uc_click is really only for detection buttons
    logger.info("Getting orders from website")
    with SB(
        uc=True,
        user_data_dir=user_data_dir,
        **kwargs,
    ) as sb:
        sb.uc_open_with_reconnect(
            "https://www.amazon.com/cpe/yourpayments/transactions",
        )
        try:
            sb.assert_text("Transactions", timeout=timeout)
        except Exception:
            logger.warning("there is a captcha here and must login within 30 seconds.")
            sb.reconnect(timeout=30)
            logger.info("reconnected")
        logger.info(f"getting data for `{max_pages}` pages")
        while current_page <= max_pages:
            next_page = 'span:contains("Next Page")'
            page_data = extract_page_data(sb)
            page_list.append(page_data)
            current_page += 1
            if not sb.is_element_clickable(next_page) or current_page > max_pages:
                break
            sb.click(next_page)
            time.sleep(2)
            sb.wait_for_element(next_page)
    logger.info(f"reached last page: `{current_page-1}`")
    website_data = pd.concat(page_list, ignore_index=True)
    website_data = website_data[
        website_data["payment_method"] != "Amazon Gift Card used"
    ]

    # get the descriptions from data dump
    data_request = pd.read_csv(amazon_dir)
    data_request["processed_product"] = (
        data_request["Product Name"].fillna("").apply(lambda x: " ".join(x.split()[:3]))
    )
    data_request = (
        data_request.groupby("Order ID")["processed_product"]
        .agg(lambda x: "Amazon - " + "; ".join(x))
        .reset_index()
    )

    # merge the description into the amazon_tx
    amazon_tx = website_data.merge(
        data_request, left_on="order_id", right_on="Order ID", how="left"
    )
    amazon_tx.drop("Order ID", axis=1, inplace=True)
    amazon_tx.rename(columns={"processed_product": "product_name"}, inplace=True)
    amazon_tx["product_name"] = amazon_tx["product_name"].fillna("")

    return amazon_tx
