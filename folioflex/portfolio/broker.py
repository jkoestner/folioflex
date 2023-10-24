"""
Broker data formatters.

There are a number of brokers that a user can have an account with and this
module contains data formatters for them. It is a growing list.

If Yodlee becomes easier to use that would be the preferred method of getting
data from brokers as it is already connecting to the brokers automatically.

"""

import logging
import numpy as np
import pandas as pd
import os

from folioflex.portfolio.helper import check_stock_dates

# logging options https://docs.python.org/3/library/logging.html
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

# provides the logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


def ally(broker_file, output_file=None, broker="ally"):
    """Format the transactions made from Ally.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to www.ally.com
    - go to Holdings & Activity
    - go to Activity
    - Copy data to .csv (UTF-8)

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    ----------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = {
        "Bought": "BUY",
        "Cash Movement": "Cash",
        "Dividend": "DIVIDEND",
        "Sold": "SELL",
    }

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # update date column type and lookup type column
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y").dt.date
    df["type"] = df["activity"].replace(type_lkup)

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": np.where(df["type"] == "Cash", "Cash", df["sym"]),
            "date": df["date"],
            "type": df["type"],
            "units": np.select(
                [(df["type"] == "Cash") | (df["type"] == "DIVIDEND")],
                [df["amount"]],
                default=df["qty"],
            ),
            "cost": df["amount"],
            "broker": broker,
        }
    )

    # check stock dates
    check_stock_dates(trades, fix=True)
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")

        trades.sort_values(by=["date", "ticker"], ascending=False, inplace=True)
        trades.to_csv(output_file, index=False)

    return trades


def fidelity(broker_file, output_file=None, broker="fidelity"):
    """Format the transactions made from Fidelity.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to www.fidelity.com/
    - go to Activity & Orders
    - download data to .csv
    - copy to new .csv and save (UTF-8)

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    ----------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = {
        "DIVIDEND": "DIVIDEND",
        "CASH DISTRIBUTN": "Cash",
        "YOU BOUGHT": "BUY",
        "REINVESTMENT": "BUY",
        "YOU SOLD": "SELL",
    }

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # update date column type
    df["date"] = pd.to_datetime(df["run_date"], format="%m/%d/%Y").dt.date

    # Loop through each type_lkup and update type
    for string, tag in type_lkup.items():
        df.loc[df["action"].str.contains(string, case=False), "type"] = tag

    # SPAXX is actually cash
    df = df.loc[~((df["symbol"] == "SPAXX") & (df["type"] == "BUY"))]
    df.loc[(df["symbol"] == "SPAXX"), "symbol"] = "Cash"

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": np.where(df["type"] == "Cash", "Cash", df["symbol"]),
            "date": df["date"],
            "type": df["type"],
            "units": np.select(
                [(df["type"] == "Cash") | (df["type"] == "DIVIDEND")],
                [df["amount_($)"]],
                default=df["quantity"],
            ),
            "cost": df["amount_($)"],
            "broker": broker,
        }
    )

    # check stock dates
    check_stock_dates(trades, fix=True)
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")

        trades.sort_values(by=["date", "ticker"], ascending=False, inplace=True)
        trades.to_csv(output_file, index=False)

    return trades


def ib(broker_file, output_file=None, broker="ib"):
    """Format the transactions made from Investment Bankers.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to https://interactivebrokers.com/
    - go to Performance & Reports > Flex Queries
    - Add new Activity Flex Query
       - Format: csv
       - Date Format: MM/dd/yyyy

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    ----------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = {
        "BUY": "BUY",
        "SELL": "SELL",
        "CASH RECEIPTS": "Cash",
        "DISBURSEMENT": "Cash",
        "DIVIDEND": "DIVIDEND",
        "CREDIT INT": "DIVIDEND",
    }

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["description"] = df["description"].fillna("") + " " + df["buy/sell"].fillna("")
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df[df["symbol"] != "Symbol"]

    # update date column type
    df["date"] = pd.to_datetime(df["datetime"], format="mixed").dt.date

    # Loop through each type_lkup and update type
    for string, tag in type_lkup.items():
        df.loc[df["description"].str.contains(string, case=False), "type"] = tag
    # Credit interest is tagged with Cash
    df.loc[df["description"].str.contains("CREDIT INT", case=False), "symbol"] = "Cash"

    # drop rows that do not have a type
    df = df.dropna(subset=["type"])

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": np.where(df["type"] == "Cash", "Cash", df["symbol"]),
            "date": df["date"],
            "type": df["type"],
            "units": np.select(
                [(df["type"] == "Cash") | (df["type"] == "DIVIDEND")],
                [df["proceeds"]],
                default=df["quantity"],
            ),
            "cost": df["proceeds"],
            "broker": broker,
        }
    )

    # check stock dates
    check_stock_dates(trades, fix=True)
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")

        trades.sort_values(by=["date", "ticker"], ascending=False, inplace=True)
        trades.to_csv(output_file, index=False)

    return trades


def ybr(broker_file, output_file=None, broker="401"):
    """Format the transactions made from ybr.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to https://ybr.com
    - go to Retirement & Savings -> Account Activity
    - download activity to .csv for each year

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    ----------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = {
        "DIVIDEND": "DIVIDEND",
        "CASH DISTRIBUTN": "Cash",
        "YOU BOUGHT": "BUY",
        "REINVESTMENT": "BUY",
        "YOU SOLD": "SELL",
    }

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # update date column type
    df["date"] = pd.to_datetime(df["run_date"], format="%m/%d/%Y").dt.date

    # Loop through each type_lkup and update type
    for string, tag in type_lkup.items():
        df.loc[df["action"].str.contains(string, case=False), "type"] = tag

    # SPAXX is actually cash
    df = df.loc[~((df["symbol"] == "SPAXX") & (df["type"] == "BUY"))]
    df.loc[(df["symbol"] == "SPAXX"), "symbol"] = "Cash"

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": np.where(df["type"] == "Cash", "Cash", df["symbol"]),
            "date": df["date"],
            "type": df["type"],
            "units": np.select(
                [(df["type"] == "Cash") | (df["type"] == "DIVIDEND")],
                [df["amount_($)"]],
                default=df["quantity"],
            ),
            "cost": df["amount_($)"],
            "broker": broker,
        }
    )

    # check stock dates
    check_stock_dates(trades, fix=True)
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")

        trades.sort_values(by=["date", "ticker"], ascending=False, inplace=True)
        trades.to_csv(output_file, index=False)

    return trades


def append_trades(trades, output_file, broker):
    """Append trades to existing trades file.

    Parameters
    ----------
    trades : DataFrame
        trades dataframe
    output_file : str
        path to trades file that will be created
    broker : str
        name of the broker

    Returns
    ----------
    trades : DataFrame
        trades dataframe

    """
    existing_trades = pd.read_csv(output_file, parse_dates=["date"])
    existing_trades["date"] = pd.to_datetime(existing_trades["date"]).dt.date
    max_date = existing_trades[existing_trades["broker"] == broker]["date"].max()
    if pd.isna(max_date):
        new_trades = (
            trades  # Since max_date is NaN, we consider all trades as new trades
        )
    else:
        new_trades = trades[trades["date"] > max_date]
    trades = pd.concat([existing_trades, new_trades], ignore_index=True)
    logger.info(
        f"Appended {len(new_trades)} rows to the {broker} trades to {output_file} "
        f"that were greater than {max_date}"
    )

    return trades
