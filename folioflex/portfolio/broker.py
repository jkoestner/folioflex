"""
Broker data formatters.

There are a number of brokers that a user can have an account with and this
module contains data formatters for them. It is a growing list.

If Yodlee becomes easier to use that would be the preferred method of getting
data from brokers as it is already connecting to the brokers automatically.

"""

import datetime as dt
import getpass
import os
import re
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd
import requests  # only yodlee

from folioflex.portfolio.helper import check_stock_dates
from folioflex.portfolio.wrappers import Yahoo
from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


def ally(
    broker_file: str, output_file: Optional[str] = None, broker: str = "ally"
) -> Union[pd.DataFrame, None]:
    """
    Format the transactions made from Ally.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to invest.ally.com
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
    -------
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
        return None
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.apply(lambda x: x.strip() if isinstance(x, str) else x)

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
    trades = check_stock_dates(trades, fix=True)["fix_tx_df"]
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")
        trades = trades.sort_values(by=["date", "ticker"], ascending=False)
        trades.to_csv(output_file, index=False)

    return trades


def fidelity(
    broker_file: str, output_file: Optional[str] = None, broker: str = "fidelity"
) -> Union[pd.DataFrame, None]:
    """
    Format the transactions made from Fidelity - Stock account.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to www.fidelity.com/
    - go to Activity & Orders
    - download data to .csv

    Notes
    -----
    - The headers seem to change, and if greater than 10 code should be updated
    - the date has had a space at beggining of string, so need to strip

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    -------
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

    def find_header_row(broker_file):
        with open(broker_file, "r") as file:
            for i, line in enumerate(file):
                if i >= 10:
                    break
                columns = [col.strip() for col in line.split(",")]
                if "Run Date" in columns:
                    logger.info(f"using header row at line {i}")
                    return i
        raise ValueError(
            "Could not find column 'Run Date' in the first 10 lines of the file"
        )

    # read in the transactions file
    try:
        skiprows = find_header_row(broker_file) - 1
        df = pd.read_csv(broker_file, skiprows=skiprows)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return None

    # cleaning dataframe by formatting columns and removing whitespace from strings
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    for column in df.columns:
        df[column] = df[column].map(lambda x: x.strip() if isinstance(x, str) else x)

    # remove footer of dataframe
    df_end = df[df["action"].isna()].index.min()
    if pd.notna(df_end):
        df = df.loc[: df_end - 1]
    else:
        pass
    start_df_len = len(df)

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
    trades = check_stock_dates(trades, fix=True)["fix_tx_df"]
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")
        trades = trades.sort_values(by=["date", "ticker"], ascending=False)
        trades.to_csv(output_file, index=False)

    return trades


def fidelity_retirement(
    broker_file: str, output_file: Optional[str] = None, broker: str = "ybr"
) -> Union[pd.DataFrame, None]:
    """
    Format the transactions made from Fidelity - Retirement account.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to www.fidelity.com/
    - go to Activity & Orders
    - download data to .csv

    Notes
    -----
    - The headers seem to change, and if greater than 10 code should be updated
    - the date has had a space at beggining of string, so need to strip

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    -------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = pd.DataFrame(
        {
            "transaction_type": [
                "Contributions",
                "Transfer In",
            ],
            "type": [
                "BUY",
                "BUY",
            ],
        }
    )

    # lookup table for symbols
    symbol_lkup = pd.DataFrame(
        {
            "investment": [
                "BTC EQUITY INDEX J",
                "BR LP INDEX 2050 F",
                "SS RSL SMMDCP IDX II",
            ],
            "symbol": [
                "BLKEQIX",
                "LIPIX",
                "SSRMIX",
            ],
            "relative": [
                "WBREOX/P10080",
                "P11540",
                "",
            ],
        }
    )

    def find_header_row(broker_file):
        with open(broker_file, "r") as file:
            for i, line in enumerate(file):
                if i >= 10:
                    break
                columns = [col.strip() for col in line.split(",")]
                if "Date" in columns:
                    logger.info(f"using header row at line {i}")
                    return i
        raise ValueError(
            "Could not find column 'Date' in the first 10 lines of the file"
        )

    # read in the transactions file
    try:
        skiprows = find_header_row(broker_file) - 1
        df = pd.read_csv(broker_file, skiprows=skiprows)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return None

    # cleaning dataframe by formatting columns and removing whitespace from strings
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.apply(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.rename(
        columns={
            "amount_($)": "cost",
            "shares/unit": "units",
        },
    )
    df["price"] = df["cost"] / df["units"]

    # remove footer of dataframe
    df_end = df[df["transaction_type"].isna()].index.min()
    if pd.notna(df_end):
        df = df.loc[: df_end - 1]
    else:
        pass
    start_df_len = len(df)

    # update date column type
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y").dt.date

    # add in symbol and type if checks pass
    missing_funds = df[~df["investment"].isin(symbol_lkup["investment"])][
        "investment"
    ].unique()
    if len(missing_funds) > 0:
        raise ValueError(
            f"Not all funds are in the symbol lookup table for instance {missing_funds}"
        )
    missing_activity = df[~df["transaction_type"].isin(type_lkup["transaction_type"])][
        "transaction_type"
    ].unique()
    if len(missing_activity) > 0:
        raise ValueError(
            f"Not all activity are in the activity lookup table "
            f"for instance {missing_activity}"
        )

    df = df.merge(symbol_lkup, on="investment", how="left")
    df = df.merge(type_lkup, on="transaction_type", how="left")

    # change to types to standardize dataset
    df["cost"] = np.where(df["type"].isin(["BUY", "SELL"]), df["cost"] * -1, df["cost"])
    df["units"] = np.where(df["type"].isin(["DIVIDEND"]), df["cost"], df["units"])

    # add cash from BUY types
    cash = df[
        df["transaction_type"].isin(
            [
                "Contributions",
            ]
        )
    ].copy()
    cash["type"] = "Cash"
    cash["symbol"] = "Cash"
    cash["cost"] = cash["cost"] * -1
    cash["units"] = cash["cost"]
    cash["price"] = 1
    df = pd.concat([df, cash]).reset_index()

    # SPAXX is actually cash
    df = df.loc[~((df["symbol"] == "SPAXX") & (df["type"] == "BUY"))]
    df.loc[(df["symbol"] == "SPAXX"), "symbol"] = "Cash"

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": np.where(df["type"] == "Cash", "Cash", df["symbol"]),
            "date": df["date"],
            "type": df["type"],
            "units": df["units"],
            "cost": df["cost"],
            "broker": broker,
        }
    )

    # check stock dates
    trades = check_stock_dates(trades, fix=True)["fix_tx_df"]
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")
        trades = trades.sort_values(by=["date", "ticker"], ascending=False)
        trades.to_csv(output_file, index=False)

    return trades


def ib(
    broker_file: str,
    output_file: Optional[str] = None,
    broker: str = "ib",
    funds: Optional[List[str]] = None,
    delisted: Optional[List[str]] = None,
) -> Union[pd.DataFrame, None]:
    """
    Format the transactions made from Investment Bankers.

    Instructions for downloading transactions:
    ------------------------------------------
    - go to https://interactivebrokers.com/
    - go to Performance & Reports > Flex Queries
    - Add new Activity Flex Query
       - Format: csv
       - Date Format: MM/dd/yyyy

    Setting up the Flex Query:
    ---------------------------
    These are the settings that were used, however there may be other types of
    transactions that could be added.
    - Trades: Execution
      - Transaction Type, Asset Class, Symbol, Date/Time, Proceeds, Description,
        Quantity, TradePrice, Buy/Sell
    - Cash Transactions: Dividends, Deposits/Withdrawals, Broker Interest Paid
      Broker Interest Received, Detail
      - Type, Asset Class, Symbol, Date/Time, Amount, Description
    - Transfers: Transfer
      - Type, Asset Class, Symbol, Date/Time, Position Amount, Description, Quantity,
        Cash Transfer, Direction
    - Corporate Actions: Detail
      - Type, Asset Class, Symbol, Date/Time, Amount, Description, Quantity

    Parameters
    ----------
    broker_file : str
        path to transactions file that was downloaded from Ally
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker
    funds : list (optional)
        list of tickers that are funds
    delisted : list (optional)
        list of tickers that are delisted

    Returns
    -------
    trades : DataFrame
        trades dataframe

    """
    if funds is None:
        funds = []
    if delisted is None:
        delisted = []
    # lookup table for types of transactions
    type_lkup = {
        "BUY": "BUY",
        "IN": "BUY",
        "SELL": "SELL",
        "CASH RECEIPTS": "Cash",
        "DISBURSEMENT": "Cash",
        "DIVIDEND": "DIVIDEND",
        "CREDIT INT": "DIVIDEND",
        "CHANGE TO": "acquisition",
        "MERGED": "acquisition",
    }

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return None
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["description"] = df["description"].fillna("") + " " + df["buy/sell"].fillna("")
    df = df.apply(lambda x: x.strip() if isinstance(x, str) else x)
    df = df[df["symbol"] != "Symbol"]  # remove header rows not first row
    df["quantity"] = df["quantity"].astype(float)
    df["proceeds"] = df["proceeds"].astype(float)
    df["tradeprice"] = df["tradeprice"].astype(float)

    # update date column type
    df["date"] = pd.to_datetime(df["datetime"], format="mixed").dt.date

    # Loop through each type_lkup and update type
    for string, tag in type_lkup.items():
        df.loc[
            df["description"].str.contains(r"\b" + string + r"\b", case=False), "type"
        ] = tag

    # Cash Transactions
    # Credit interest is tagged with Cash
    df.loc[df["description"].str.contains("CREDIT INT", case=False), "symbol"] = "Cash"

    # Transfers
    # Transfer cash transactions need to update the proceeds column
    if (df["buy/sell"] == "IN").any():
        logger.info("Updating IB TRANSFER transactions")
        df.loc[df["buy/sell"] == "IN", "proceeds"] = (
            df.loc[df["buy/sell"] == "IN", "proceeds"] * -1
        )
        cash = df[(df["buy/sell"] == "IN") & (df["assetclass"] != "CASH")].copy()
        cash["type"] = "Cash"
        cash["symbol"] = "Cash"
        cash["proceeds"] = cash["proceeds"] * -1
        df = pd.concat([df, cash]).reset_index()
        df.loc[df["assetclass"] == "CASH", "proceeds"] = df["tradeprice"]
        df.loc[df["assetclass"] == "CASH", "symbol"] = "Cash"
        df.loc[df["assetclass"] == "CASH", "type"] = "Cash"

    # Corporate Actions
    # acquisition transactions need to be adjusted
    # the data from IB is not rich so there is regex to extract the old and new symbols
    # and then the proceeds and tradeprice are updated from historical price data
    acquisitions = df[df["type"] == "acquisition"].copy()
    if not acquisitions.empty:
        logger.info("Updating IB ACQUISITION transactions")
        df = df[df["type"] != "acquisition"]
        orig_symbol_pattern = r"^([^\(]+)"
        new_symbol_pattern = r"\(([^,(]+),"
        acquisitions["orig_symbol"] = acquisitions["description"].apply(
            lambda x: re.search(orig_symbol_pattern, x).group(0)
        )
        acquisitions["new_symbol"] = acquisitions["description"].apply(
            lambda x: re.search(new_symbol_pattern, x).group(1)
        )

        # remove .OLD from the symbol
        acquisitions["new_symbol"] = acquisitions["new_symbol"].str.replace(".OLD", "")

        # update the new symbol
        acquisition_symbol_lkup = acquisitions[
            acquisitions["orig_symbol"] != acquisitions["new_symbol"]
        ][["orig_symbol", "new_symbol"]]
        acquisitions = acquisitions.set_index("orig_symbol")
        acquisitions.update(acquisition_symbol_lkup.set_index("orig_symbol"))
        acquisitions = acquisitions.reset_index()

        # update acquisition tickers transaction prices
        acquisition_symbol_lkup = acquisitions.reset_index()[
            ["new_symbol", "orig_symbol", "date"]
        ].drop_duplicates()
        df = df.merge(
            acquisition_symbol_lkup.rename(columns={"orig_symbol": "symbol"})[
                ["new_symbol", "symbol"]
            ],
            on="symbol",
            how="left",
        )
        df["symbol"] = np.where(df["new_symbol"].isna(), df["symbol"], df["new_symbol"])
        df = df.drop(columns=["new_symbol"])
        acquisition_tickers = list(acquisition_symbol_lkup["new_symbol"])
        acquisition_tickers = [
            tick for tick in acquisition_tickers if tick not in funds + delisted
        ]
        acquisition_min_year = acquisition_symbol_lkup["date"].min().year
        acquisition_price_history = Yahoo().stock_history(
            tickers=acquisition_tickers, min_year=acquisition_min_year
        )

        # add in the stock price at transition
        acquisition_price_history = acquisition_price_history.rename(
            columns={"ticker": "new_symbol"}
        )
        acquisition_price_history = acquisition_price_history.sort_values(by="date")
        acquisitions = pd.merge_asof(
            acquisitions,
            acquisition_price_history,
            on="date",
            by="new_symbol",
            direction="nearest",
        )
        acquisitions["tradeprice"] = acquisitions["last_price"]
        acquisitions["proceeds"] = (
            acquisitions["last_price"] * -acquisitions["quantity"]
        )
        acquisitions["type"] = np.where(acquisitions["quantity"] < 0, "SELL", "BUY")
        acquisitions["type"] = np.where(
            np.isnan(acquisitions["tradeprice"]), np.nan, acquisitions["type"]
        )
        acquisitions["symbol"] = acquisitions["new_symbol"]
        acquisitions = acquisitions.drop(
            columns=["orig_symbol", "new_symbol", "last_price", "stock_splits"]
        )

        # append df with acquisitions
        df = pd.concat([df, acquisitions]).reset_index()

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
    trades = check_stock_dates(trades, fix=True)["fix_tx_df"]
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")
        trades = trades.sort_values(by=["date", "ticker"], ascending=False)
        trades.to_csv(output_file, index=False)

    return trades


def ybr(
    broker_file: str,
    output_file: Optional[str] = None,
    broker: str = "ybr",
    reinvest: bool = True,
) -> Union[pd.DataFrame, None]:
    """
    Format the transactions made from ybr.

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
    reinvest : bool (optional)
        whether or not to reinvest dividends into the fund, default is True

    Returns
    -------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = pd.DataFrame(
        {
            "activity_type": [
                "Company Matching Contributions",
                "Employee 401(k) Contributions",
                "Employer Supplemental Contributions",
                "Genworth Fund Reunitization",
                "Dividends",
                "Fund Reallocation",
                "Fund Transfers",
                "Revenue Sharing",
                "Genworth Fund Liquidation 1",
            ],
            "type": [
                "BUY",
                "BUY",
                "BUY",
                "BOOK",
                "DIVIDEND",
                "SELL",
                "BUY",
                "DIVIDEND",
                "SELL",
            ],
        }
    )

    # lookup table for symbols
    symbol_lkup = pd.DataFrame(
        {
            "fund": [
                "Dodge and Cox Income",
                "BlackRock Equity Index",
                "T.Rowe Price Institutional Large Cap Growth Fund",
                "Genworth Stock Fund",
                "T. Rowe Price Stable Value",
                "BlackRock LifePath Index 2050",
                "BlackRock Russell 2000 Value Index Fund",
                "BlackRock LifePath Index 2050 RAF",
                "BlackRock Russell 2000 Growth Index Fund",
                "Harding Loevner International Equity",
                "SSGA Russell Small/Mid Cap Index",
            ],
            "symbol": [
                "DODIX",
                "BLKEQIX",
                "TRPILCG",
                "TRPSV",
                "GNW",
                "LIPIX",
                "BLKRVIX",
                "LIPIX",
                "BLKRGIX",
                "HLIEIX",
                "SSRMIX",
            ],
            "relative": [
                "",
                "WBREOX/P10080",
                "TPLGX/P10280",
                "",
                "P10230",
                "P11540",
                "WBRRDX/NP4199",
                "",
                "WBRRFX/P11950",
                "HLMIX/P11210",
                "",
            ],
        }
    )

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return None
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.apply(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.rename(
        columns={
            "amount": "cost",
            "fund_nav/price": "price",
            "fund_units": "units",
        },
    )

    # update date column type
    df["date"] = pd.to_datetime(df["valuation_date"], format="%m-%d-%Y").dt.date

    # add in symbol and type if checks pass
    missing_funds = df[~df["fund"].isin(symbol_lkup["fund"])]["fund"].unique()
    if missing_funds:
        raise ValueError(
            f"Not all funds are in the symbol lookup table for instance {missing_funds}"
        )
    missing_activity = df[~df["activity_type"].isin(type_lkup["activity_type"])][
        "activity_type"
    ].unique()
    if missing_activity:
        raise ValueError(
            f"Not all activity are in the activity lookup table "
            f"for instance {missing_activity}"
        )

    df = df.merge(symbol_lkup, on="fund", how="left")
    df = df.merge(type_lkup, on="activity_type", how="left")

    # change to types to standardize dataset
    df["cost"] = np.where(df["type"].isin(["BUY", "SELL"]), df["cost"] * -1, df["cost"])
    df["units"] = np.where(df["type"].isin(["DIVIDEND"]), df["cost"], df["units"])

    # add cash from BUY types
    cash = df[
        df["activity_type"].isin(
            [
                "Company Matching Contributions",
                "Employee 401(k) Contributions",
                "Employer Supplemental Contributions",
            ]
        )
    ].copy()
    cash["type"] = "Cash"
    cash["symbol"] = "Cash"
    cash["cost"] = cash["cost"] * -1
    cash["units"] = cash["cost"]
    cash["price"] = 1
    df = pd.concat([df, cash]).reset_index()

    # add stock from DIVIDEND types that get reinvested
    if reinvest:
        reinvest_df = df[df["type"] == "DIVIDEND"].copy()
        reinvest_df["type"] = "BUY"
        reinvest_df["units"] = reinvest_df["cost"] / reinvest_df["price"]
        reinvest_df["cost"] = reinvest_df["cost"] * -1
        df = pd.concat([df, reinvest_df]).reset_index()

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": df["symbol"],
            "date": df["date"],
            "type": df["type"],
            "units": df["units"],
            "cost": df["cost"],
            "broker": broker,
        }
    )

    # check stock dates
    trades = check_stock_dates(trades, fix=True)["fix_tx_df"]
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")

        trades = trades.sort_values(by=["date", "ticker"], ascending=False)
        trades.to_csv(output_file, index=False)

    return trades


class Yodlee:
    """
    A class that connects to the Yodlee developer platform.

    WARNING: This class is not fully supported as it requires API keys from
    Yodlee and there is a cost to maintain. If a free tier becomes available
    or cost is reasonable will use this class to get transactions from brokers.

    The developer site is:
    https://developer.envestnet.com/yodlee/

    The API documentation is:
    https://developer.envestnet.com/resources/yodlee/data-model/docs

    The FastLink API documentation is:
    https://developer.envestnet.com/resources/yodlee/fastlink-4/docs/api_integrations

    There are 2 separate pieces to using the Yodless to provide transactions.

    FastLink - Server to connect to the broker
    ------------------------------------------
    FastLink is a server that allows the connection to the broker. The connection
    was authorized to pull in the following to allow the largest amount of brokers.
    - Aggregation

    Once a user is logged in and connects to the broker it allows the API to then
    connect to that broker.

    The Launch tier was selected as it is free and allows for 100 activities, which
    where an activity is creation of an account, but only available for 90 days.

    Developer can only be used as Production will only work where the app is registered
    with the providers.

    A way to see which banks are available is by going to the dashboard liveconfig
    and going to site selection and choosing the banks that are available.
    https://developer.envestnet.com/yodlee/user/me/dashboard/liveconfig

    This was a helpful resource understanding how to set up:
    https://web.postman.co/workspace/
    d3ac0acd-bc2f-4a29-83ef-384ab5f28972/collection/
    20005268-515b1d2c-453a-4ea3-980c-ce42b25c9590

    API - Query the transactions
    ----------------------------
    Once the user has connected to the broker, the API can be used to query the
    transactions.

    """

    def __init__(
        self,
        yodlee_login_name: str,
    ) -> None:
        """Initialize the Yodlee class."""
        self.yodlee_login_name = yodlee_login_name
        self.yodlee_client_id = config_helper.YODLEE_CLIENT_ID
        self.yodlee_secret = config_helper.YODLEE_SECRET
        self.yodlee_endpoint = config_helper.YODLEE_ENDPOINT
        for var in [self.yodlee_client_id, self.yodlee_secret, self.yodlee_endpoint]:
            if not var:
                raise ValueError(f"Yodlee `{var}` is not set")
        self.headers = {
            "Api-Version": "1.1",  # Replace with the appropriate version
            "Content-Type": "application/x-www-form-urlencoded",
            "loginName": self.yodlee_login_name,
        }

        self.user_token = self.get_user_token()
        logger.info(f"Yodlee user token created for {self.yodlee_login_name}")
        self.headers_authorized = {
            "Api-Version": "1.1",  # Replace with the appropriate version
            "Authorization": "Bearer " + self.user_token,
            "Content-Type": "application/json",
        }

    def refresh_token(self) -> None:
        """
        Refresh the broker.

        This will refresh the broker to get the latest transactions.

        """
        self.user_token = self.get_user_token()

    def get_user_token(self) -> str:
        """
        Get the user token for the yodlee user.

        Returns
        -------
        yodlee_user_token : str
            yodlee user token

        """
        payload = {"clientId": self.yodlee_client_id, "secret": self.yodlee_secret}
        response = requests.post(
            self.yodlee_endpoint + "auth/token", data=payload, headers=self.headers
        )

        # raise error if status code is not 201
        response_success = 201
        if response.status_code != response_success:
            raise ValueError(
                f"Yodlee user token not created for {self.yodlee_login_name} "
                f"with status code {response.status_code}"
            )

        response_data = response.json()
        user_token = response_data.get("token").get("accessToken")

        return user_token

    def get_accounts(self, id: str = "") -> pd.DataFrame:
        """
        Get the accounts for the yodlee user.

        These are the individual accounts for a user.

        Parameters
        ----------
        id : str (optional)
            account to get transactions for, if '' get all accounts

        Returns
        -------
        accounts : DataFrame
            accounts dataframe

        """
        headers = self.headers_authorized
        response = requests.get(
            self.yodlee_endpoint + "/accounts/" + id, headers=headers
        )
        response_data = response.json()
        accounts = pd.DataFrame(response_data["account"]).sort_values(
            by="lastUpdated", ascending=False
        )

        return accounts

    def get_provider_accounts(self, id: str = "") -> pd.DataFrame:
        """
        Get the provider accounts for the yodlee user.

        These are the provider accounts for a user and gives information
        relate to when it has been updated.

        Parameters
        ----------
        id : str (optional)
            provider_accounts to get transactions for, if '' get all provider_accounts

        Returns
        -------
        provider_accounts : DataFrame
            provider_accounts dataframe

        """
        headers = self.headers_authorized
        response = requests.get(
            self.yodlee_endpoint + "/providerAccounts/" + id, headers=headers
        )
        response_data = response.json()
        provider_accounts = pd.DataFrame(response_data["providerAccount"]).sort_values(
            by="lastUpdated", ascending=False
        )

        return provider_accounts

    def delete_provider_accounts(self, id: str = "") -> requests.models.Response:
        """
        Delete the provider account for the yodlee user.

        Parameters
        ----------
        id : str (optional)
            provider_accounts to get transactions for, if '' get all provider_accounts

        Returns
        -------
        response : dict
            JSON content from the delete request response.

        """
        headers = self.headers_authorized
        response = requests.delete(
            self.yodlee_endpoint + "/providerAccounts/" + id, headers=headers
        )

        return response

    def get_providers(self, id: str = "") -> pd.DataFrame:
        """
        Get the provider accounts for the yodlee user.

        These are the providers and gives information on what the provider is.

        Parameters
        ----------
        id : str (optional)
            providers to get transactions for, if '' get all providers

        Returns
        -------
        providers : DataFrame
            providers dataframe

        """
        headers = self.headers_authorized
        response = requests.get(
            self.yodlee_endpoint + "/providers/" + id, headers=headers
        )
        response_data = response.json()
        providers = pd.DataFrame(response_data["provider"]).sort_values(
            by="lastModified", ascending=False
        )

        return providers

    def get_holdings(self, provider_account_id: str = "") -> pd.DataFrame:
        """
        Get the holdings accounts for the yodlee user.

        These are the holdings in a specific account

        Parameters
        ----------
        provider_account_id : str (optional)
            providers account id to get holdings for, if '' get all providers

        Returns
        -------
        holdings : DataFrame
            holdings dataframe

        """
        headers = self.headers_authorized
        if provider_account_id:
            provider_account_id = "?providerAccountId=" + provider_account_id
        response = requests.get(
            self.yodlee_endpoint + "/holdings" + provider_account_id, headers=headers
        )
        response_data = response.json()
        holdings = pd.DataFrame(response_data["holding"]).sort_values(
            by="lastUpdated", ascending=False
        )

        return holdings

    def get_transactions(
        self, account_id: str = "", formatter: bool = False
    ) -> pd.DataFrame:
        """
        Get the transactions for accounts for the yodlee user.

        These are the transactions in a specific account

        Parameters
        ----------
        account_id : str (optional)
            account id to get transactions for, if '' get all providers
        formatter : bool (optional)
            whether or not to format the transactions

        Returns
        -------
        transactions : DataFrame
            transactions dataframe

        """
        headers = self.headers_authorized
        if account_id:
            account_id = "?accountId=" + account_id
        response = requests.get(
            self.yodlee_endpoint + "/transactions" + account_id, headers=headers
        )
        response_data = response.json()
        transactions = pd.DataFrame(response_data["transaction"]).sort_values(
            by="lastUpdated", ascending=False
        )

        # format transactions into standardized format
        if formatter:
            formatted_transactions = []
            for transaction in response_data["transaction"]:
                flat_transaction = {
                    "symbol": transaction.get("symbol", None),
                    "amount": transaction["amount"].get("amount", None)
                    if "amount" in transaction
                    else None,
                    "transactionDate": transaction.get("transactionDate", None),
                    "type": transaction.get("type", None),
                    "baseType": transaction.get("baseType", None),
                    "price": transaction["price"].get("amount", None)
                    if "price" in transaction
                    else None,
                    "quantity": transaction.get("quantity", None),
                }
                formatted_transactions.append(flat_transaction)
            transactions = pd.DataFrame(formatted_transactions).sort_values(
                by="transactionDate", ascending=False
            )

        return transactions


def append_trades(trades, output_file: str, broker: str) -> pd.DataFrame:
    """
    Append trades to existing trades file.

    Parameters
    ----------
    trades : DataFrame
        trades dataframe
    output_file : str
        path to trades file that will be created
    broker : str
        name of the broker

    Returns
    -------
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


class Robinhood:
    """
    Pull account activity from Robinhood using the unofficial pyhood client.

    Security notes
    --------------
    - Tokens are cached as plain JSON in ~/.pyhood/session.json. Call
      `logout()` when done so the tokens are revoked and the file is deleted.

    Parameters
    ----------
    token_path : str (optional)
        where pyhood caches the session, default ~/.pyhood/session.json.

    """

    def __init__(self, token_path: Optional[str] = None) -> None:
        """Initialize the Robinhood class."""
        from pyhood.auth import DEFAULT_TOKEN_DIR, DEFAULT_TOKEN_FILE

        self.token_path = (
            Path(token_path) if token_path else DEFAULT_TOKEN_DIR / DEFAULT_TOKEN_FILE
        )
        self.session = None
        self.client = None

    def login(self, username: Optional[str] = None, timeout: int = 120) -> None:
        """
        Log in to Robinhood.

        Reuses a cached session if one exists. Otherwise prompts for the
        password (hidden input) and, the first time on a device, waits for
        you to tap "Yes, it's me" in the Robinhood app.

        Parameters
        ----------
        username : str (optional)
            Robinhood email, prompted for if needed and not given
        timeout : int (optional), default 120
            seconds to wait for device approval

        """
        import pyhood
        from pyhood.client import PyhoodClient
        from pyhood.exceptions import AuthError, MFARequiredError

        try:
            self.session = pyhood.login(token_path=self.token_path, timeout=timeout)
            logger.info("Using cached Robinhood session")
        except MFARequiredError:
            raise
        except AuthError:
            username = username or input("Robinhood username (email): ")
            password = getpass.getpass("Robinhood password: ")
            logger.info("Check the Robinhood app to approve this device if prompted")
            try:
                self.session = pyhood.login(
                    username=username,
                    password=password,
                    token_path=self.token_path,
                    timeout=timeout,
                )
            except MFARequiredError:
                code = input("MFA code: ")
                self.session = pyhood.login(
                    username=username,
                    password=password,
                    mfa_code=code,
                    token_path=self.token_path,
                    timeout=timeout,
                )
            finally:
                del password

        self.client = PyhoodClient(self.session)
        logger.info(f"Logged in to Robinhood, session cached at {self.token_path}")

    def logout(self, verify: bool = True) -> dict:
        """
        Revoke the Robinhood tokens and delete the cached session file.

        With `verify=True` each token is tested afterwards:
        - access token: a read request should now be rejected (401)
        - refresh token: a refresh grant should now be refused

        If the refresh token still works, the test itself mints a new token
        pair; its access token is revoked immediately and a warning tells you
        to remove the device in the Robinhood app's security settings.

        Parameters
        ----------
        verify : bool (optional)
            test that the tokens are dead after revoking, default True

        Returns
        -------
        status : dict
            {"access_token": ..., "refresh_token": ...} with one of
            "revoked" (rejected with 401/403 or invalid_grant),
            "alive" (accepted with 200), "unverified" (any other response,
            or verify=False), or "missing" (no token in the session file)

        """
        import pyhood
        from pyhood.auth import TokenStore

        store = TokenStore(self.token_path)
        cached = store.load() or {}
        status = {}

        # access token first: the refresh token can mint new access tokens,
        # but not the other way round, so this order leaves nothing usable
        # even if the refresh revoke is the call that fails
        for kind in ("access_token", "refresh_token"):
            token = cached.get(kind)
            if not token:
                status[kind] = "missing"
                continue
            code = self._revoke(token, kind)
            logger.info(f"Revoke {kind}: returned {code}")
            status[kind] = "unverified"

        if verify and cached:
            if status["access_token"] != "missing":
                status["access_token"] = self._check_access(cached)
            if status["refresh_token"] != "missing":
                status["refresh_token"] = self._check_refresh(cached)
            if "alive" in status.values():
                logger.warning(
                    "A token is still usable. Remove this device from the device "
                    "list in the Robinhood app's security settings to kill the session."
                )
            elif "unverified" in status.values():
                logger.warning(
                    "Could not confirm every token is dead (see status codes above). "
                    "Removing this device in the Robinhood app's security settings "
                    "will end the session for certain."
                )

        pyhood.logout()
        store.clear()
        self.session = None
        self.client = None

        if self.token_path.exists():
            logger.warning(f"Session file still exists at {self.token_path}")
        else:
            logger.info(f"Deleted {self.token_path}")
        return status

    @staticmethod
    def _headers() -> dict:
        """Robinhood request headers pyhood uses, without any auth."""
        from pyhood.http import Session

        headers = Session().headers
        headers.pop("Authorization", None)
        return headers

    def _revoke(self, token: str, kind: str) -> Union[int, str]:
        """POST the token to the revoke endpoint; return the status code."""
        from pyhood import urls
        from pyhood.auth import CLIENT_ID

        try:
            resp = requests.post(
                urls.LOGOUT,
                data={"client_id": CLIENT_ID, "token": token, "token_type_hint": kind},
                headers=self._headers(),
                timeout=15,
            )
            return resp.status_code
        except requests.RequestException as e:
            return f"error ({e})"

    @staticmethod
    def _error_detail(resp: "requests.Response") -> str:
        """Short, token-free description of a Robinhood error response."""
        try:
            body = resp.json()
        except ValueError:
            return ""
        if not isinstance(body, dict):
            return ""
        parts = [str(body[k]) for k in ("error", "detail") if body.get(k)]
        return f" ({'; '.join(parts)[:120]})" if parts else ""

    def _check_access(self, cached: dict) -> str:
        """
        Test the access token with a read request.

        200 -> "alive", 401/403 -> "revoked", anything else -> "unverified".
        """
        from pyhood import urls

        headers = self._headers()
        headers["Authorization"] = (
            f"{cached.get('token_type', 'Bearer')} " + cached["access_token"]
        )
        try:
            resp = requests.get(
                urls.POSITIONS, params={"nonzero": "true"}, headers=headers, timeout=15
            )
        except requests.RequestException as e:
            logger.warning(f"access_token check: request failed ({e})")
            return "unverified"

        code = resp.status_code
        if code == 200:
            state = "alive"
        elif code in (401, 403):
            state = "revoked"
        else:
            state = "unverified"
        logger.info(
            f"access_token check: GET positions returned {code}"
            f"{self._error_detail(resp) if code != 200 else ''} -> {state}"
        )
        return state

    def _check_refresh(self, cached: dict) -> str:
        """
        Test the refresh token with a refresh grant.

        200 -> "alive" (the new pair it minted is revoked straight away),
        400/401 with an OAuth `invalid_grant` error -> "revoked",
        anything else -> "unverified".
        """
        from pyhood import urls
        from pyhood.auth import CLIENT_ID

        try:
            resp = requests.post(
                urls.LOGIN,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": cached["refresh_token"],
                    "scope": "internal",
                    "client_id": CLIENT_ID,
                    "device_token": cached.get("device_token", ""),
                    "expires_in": 60,
                },
                headers=self._headers(),
                timeout=15,
            )
        except requests.RequestException as e:
            logger.warning(f"refresh_token check: request failed ({e})")
            return "unverified"

        code = resp.status_code
        detail = self._error_detail(resp) if code != 200 else ""
        if code == 200:
            state = "alive"
        elif code in (400, 401) and "invalid_grant" in detail:
            state = "revoked"
        else:
            state = "unverified"
        logger.info(
            f"refresh_token check: refresh grant returned {code}{detail} -> {state}"
        )

        if state == "alive":
            # the test just minted a new pair, so revoke those too
            new = resp.json()
            for kind in ("access_token", "refresh_token"):
                if new.get(kind):
                    code = self._revoke(new[kind], kind)
                    logger.info(f"Revoke new {kind} from check: returned {code}")
        return state

    def _require_login(self) -> None:
        if self.client is None:
            raise RuntimeError("Not logged in. Call `login()` first.")

    def accounts(self) -> pd.DataFrame:
        """
        List every account on the login.

        Returns
        -------
        accounts : DataFrame
            one row per account, raw fields from Robinhood

        """
        self._require_login()
        return pd.json_normalize(self.client.get_all_accounts())

    def find_account(self, keyword: str = "roth") -> str:
        """
        Find an account number by its brokerage account type.

        Parameters
        ----------
        keyword : str (optional)
            text to look for in `brokerage_account_type` (case-insensitive),
            e.g. "roth" matches "ira_roth"

        Returns
        -------
        account_number : str
            the matching account number

        """
        accounts = self.accounts()
        acct_type = (
            accounts["brokerage_account_type"].fillna("").astype(str).str.lower()
        )
        matches = accounts[acct_type.str.contains(keyword.lower(), regex=False)]

        if len(matches) != 1:
            raise ValueError(
                f"Found {len(matches)} accounts with '{keyword}' in "
                f"brokerage_account_type: {accounts['brokerage_account_type'].tolist()}"
            )

        account_number = str(matches.iloc[0]["account_number"])
        logger.info(
            f"Matched '{keyword}' to {matches.iloc[0]['brokerage_account_type']} "
            f"account ending {account_number[-4:]}"
        )
        return account_number

    def get_df(
        self,
        account_number: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_dividends: bool = True,
        output_file: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get filled stock trades and paid dividends for one account.

        Notes
        -----
        - pyhood's `get_stock_orders` can't filter by account and drops the
          account field, so the orders endpoint is called directly with
          `account_number`, and each order's account is checked as a guard.
        - Only executed quantity is used, so partial fills are handled and
          cancelled/unfilled orders are dropped.
        - Option orders and cash contributions/transfers are NOT included.

        Parameters
        ----------
        account_number : str
            Robinhood account number (e.g. the Roth IRA number)
        start_date : str (optional), default is YTD
            ISO date to pull from (inclusive)
        end_date : str (optional), default is YTD
            ISO date to pull through (inclusive)
        include_dividends : bool (optional)
            whether to include dividend rows, default is True
        output_file : str (optional)
            path to save the activity csv (the `broker_file` for `robinhood`)

        Returns
        -------
        activity : DataFrame
            columns: date, symbol, activity, quantity, price, amount, fees, id
            where amount is the signed cash impact (buys negative)

        """
        from pyhood import urls

        self._require_login()
        session = self.session

        if start_date is None:
            start_date = f"{dt.date.today().year}-01-01"
        start_ts = pd.Timestamp(start_date, tz="America/New_York")
        end_ts = (
            pd.Timestamp(end_date, tz="America/New_York") + pd.Timedelta(days=1)
            if end_date
            else None
        )

        def in_range(ts: pd.Timestamp) -> bool:
            return ts >= start_ts and (end_ts is None or ts < end_ts)

        # stock orders
        raw_orders = session.get_paginated(
            urls.ORDERS,
            params={
                "account_number": account_number,
                "created_at[gte]": start_ts.tz_convert("UTC").strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            },
        )
        rows = []
        for o in raw_orders:
            filled_qty = float(o.get("cumulative_quantity") or 0)
            if o.get("legs") or filled_qty == 0:
                continue  # option orders and anything that never executed
            if account_number not in (o.get("account") or ""):
                continue  # guard in case the server ignored the account filter
            executions = o.get("executions") or []
            exec_time = min(
                (e.get("timestamp") for e in executions if e.get("timestamp")),
                default=o.get("last_transaction_at") or o.get("created_at"),
            )
            ts = pd.Timestamp(exec_time).tz_convert("America/New_York")
            if not in_range(ts):
                continue
            notional = (
                sum(
                    float(e.get("price") or 0) * float(e.get("quantity") or 0)
                    for e in executions
                )
                or float(o.get("average_price") or 0) * filled_qty
            )
            fees = float(o.get("fees") or 0)
            is_buy = o.get("side") == "buy"
            rows.append(
                {
                    "date": ts,
                    "symbol": (o.get("symbol") or "").upper(),
                    "activity": "BUY" if is_buy else "SELL",
                    "quantity": filled_qty,
                    "price": notional / filled_qty,
                    "amount": -(notional + fees) if is_buy else notional - fees,
                    "fees": fees,
                    "id": o.get("id"),
                    "instrument": o.get("instrument"),
                }
            )
        logger.info(f"Pulled {len(rows)} filled orders")

        # dividends
        if include_dividends:
            n_orders = len(rows)
            for d in session.get_paginated(urls.DIVIDENDS):
                if d.get("state") != "paid":
                    continue
                if account_number not in (d.get("account") or ""):
                    continue
                paid = pd.Timestamp(d.get("paid_at") or d.get("payable_date"))
                paid = (
                    paid.tz_localize("America/New_York")
                    if paid.tzinfo is None
                    else paid.tz_convert("America/New_York")
                )
                if not in_range(paid):
                    continue
                amount = float(d.get("amount") or 0)
                rows.append(
                    {
                        "date": paid,
                        "symbol": "",
                        "activity": "DIVIDEND",
                        "quantity": float(d.get("position") or 0),
                        "price": float(d.get("rate") or 0),
                        "amount": amount,
                        "fees": 0.0,
                        "id": d.get("id"),
                        "instrument": d.get("instrument"),
                    }
                )
            logger.info(f"Pulled {len(rows) - n_orders} paid dividends")

        cols = [
            "date",
            "symbol",
            "activity",
            "quantity",
            "price",
            "amount",
            "fees",
            "id",
        ]
        activity = pd.DataFrame(rows, columns=[*cols, "instrument"])

        # resolve missing symbols (dividends, older orders) from instrument urls
        missing = activity["symbol"] == ""
        if missing.any():
            lkup = {
                url: session.get(url).get("symbol", "")
                for url in activity.loc[missing, "instrument"].dropna().unique()
            }
            activity.loc[missing, "symbol"] = activity.loc[missing, "instrument"].map(
                lkup
            )
        activity = activity[cols]

        if activity.empty:
            logger.warning(
                f"No activity found for account ending {account_number[-4:]} "
                f"since {start_date}. If you expected trades, the orders endpoint "
                "may be ignoring account_number for this account."
            )
        else:
            activity["date"] = activity["date"].dt.date
            activity = activity.sort_values(["date", "symbol"]).reset_index(drop=True)
            activity["amount"] = activity["amount"].round(2)

        if output_file is not None:
            activity.to_csv(output_file, index=False)
            logger.info(f"Saved {len(activity)} rows to {output_file}")

        return activity


def robinhood(
    broker_file: str, output_file: Optional[str] = None, broker: str = "robinhood"
) -> Union[pd.DataFrame, None]:
    """
    Format the transactions made from Robinhood.

    Instructions for downloading transactions:
    ------------------------------------------
    - use the `Robinhood` class in this module:
      login() -> find_account() -> get_df(output_file=...) -> logout()
    - the saved csv is the `broker_file` for this function

    Parameters
    ----------
    broker_file : str
        path to activity file
    output_file : str (optional)
        path to trades file that will be created
    broker : str (optional)
        name of the broker

    Returns
    -------
    trades : DataFrame
        trades dataframe

    """
    # lookup table for types of transactions
    type_lkup = {
        "BUY": "BUY",
        "SELL": "SELL",
        "DIVIDEND": "DIVIDEND",
    }

    # read in the transactions file
    try:
        df = pd.read_csv(broker_file)
    except FileNotFoundError:
        logger.error("Transactions file not found")
        return None
    start_df_len = len(df)

    # cleaning dataframe by formatting columns and removing whitespace
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    missing_activity = df.loc[~df["activity"].isin(type_lkup), "activity"].unique()
    if len(missing_activity) > 0:
        raise ValueError(
            f"Not all activity are in the activity lookup table "
            f"for instance {missing_activity}"
        )

    # update date column type and lookup type column
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d").dt.date
    df["type"] = df["activity"].map(type_lkup)

    # standardize column and data
    trades = pd.DataFrame(
        {
            "ticker": df["symbol"],
            "date": df["date"],
            "type": df["type"],
            "units": np.select(
                [df["type"] == "DIVIDEND", df["type"] == "SELL"],
                [df["amount"], -df["quantity"]],
                default=df["quantity"],
            ),
            "cost": df["amount"],
            "broker": broker,
        }
    )

    # check stock dates
    trades = check_stock_dates(trades, fix=True)["fix_tx_df"]
    logger.info(
        f"There were {start_df_len} and now there are {len(trades)} rows in "
        f"the {broker} transactions file after cleaning"
    )

    if output_file is not None:
        if os.path.exists(output_file):
            trades = append_trades(trades, output_file, broker)
        else:
            logger.warning(f"{output_file} does not exist. Creating new file.")
        trades = trades.sort_values(by=["date", "ticker"], ascending=False)
        trades.to_csv(output_file, index=False)

    return trades
