"""
Broker data formatters.

There are a number of brokers that a user can have an account with and this
module contains data formatters for them. It is a growing list.

If Yodlee becomes easier to use that would be the preferred method of getting
data from brokers as it is already connecting to the brokers automatically.

"""

import os
import re

import numpy as np
import pandas as pd
import requests  # only yodlee

from folioflex.portfolio.helper import check_stock_dates
from folioflex.portfolio.wrappers import Yahoo
from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


def ally(broker_file, output_file=None, broker="ally"):
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
        return
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


def fidelity(broker_file, output_file=None, broker="fidelity"):
    """
    Format the transactions made from Fidelity.

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
        return

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
    df["date"] = pd.to_datetime(df["run_date"], format="%b-%d-%Y").dt.date

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


def ib(broker_file, output_file=None, broker="ib", funds=None, delisted=None):
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
        return
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


def ybr(broker_file, output_file=None, broker="ybr", reinvest=True):
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
        return
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
        yodlee_login_name,
    ):
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

    def refresh_token(self):
        """
        Refresh the broker.

        This will refresh the broker to get the latest transactions.

        """
        self.user_token = self.get_user_token()

    def get_user_token(self):
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

    def get_accounts(self, id=""):
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

    def get_provider_accounts(self, id=""):
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

    def delete_provider_accounts(self, id=""):
        """
        Delete the provider account for the yodlee user.

        Parameters
        ----------
        id : str (optional)
            provider_accounts to get transactions for, if '' get all provider_accounts

        Returns
        -------
        response : json
            response from delete request

        """
        headers = self.headers_authorized
        response = requests.delete(
            self.yodlee_endpoint + "/providerAccounts/" + id, headers=headers
        )

        return response

    def get_providers(self, id=""):
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

    def get_holdings(self, provider_account_id=""):
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

    def get_transactions(self, account_id="", formatter=False):
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


def append_trades(trades, output_file, broker):
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
