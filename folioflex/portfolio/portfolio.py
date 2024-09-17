"""
Creates classes and functions to analyze a portfolio of stocks.

The Portfolio class has a number of objects, such as:
   - file : the transaction file locations
   - funds : symbols that are considered funds
   - transactions : the transactions the occured
   - transaction_history : provides the symbol price history
   - return_view : provides the return view of the portfolio

   There are function in class as well:
   - perfomance : this function will provide the performance of portfolio

The Manager class has a number of objects, such as:
    - portfolios : the portfolios that are managed

    There are functions in class as well:
    - get_summary : this function will provide the summary of all portfolios

"""

import os
from datetime import timedelta

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import plotly.express as px
from pyxirr import xirr

from folioflex.portfolio.helper import (
    check_stock_dates,
    convert_date_to_timezone,
    convert_lookback,
)
from folioflex.portfolio.wrappers import Yahoo
from folioflex.utils import config_helper, custom_logger

pd.options.display.float_format = "{:,.2f}".format

logger = custom_logger.setup_logging(__name__)


class Portfolio:
    """
    A Portfolio class used to provide analysis of a portfolio.

    The class requires a transaction file to be provided. The transaction file
    will have sales and buys to then develop a return of the portfolio as well
    as a return of the different assets that were purchased.

    There are a number of options that the user can provide to filter the analysis
    to a particular subset of transactions or brokers. There are also options to
    provide a list of funds or delisted stocks so that when the ticker price history
    is downloaded from yahoo finance, the price history is not downloaded and instead
    use the price of the transactions.

    Parameters
    ----------
    config_path : str
        the location of the config file
    portfolio : str
        the name of the portfolio to analyze

    """

    def __init__(
        self,
        config_path,
        portfolio,
    ):
        """Initialize the Portfolio class."""
        config_dict = config_helper.get_config_options(config_path, portfolio)
        self.file = self.load_filename(config_dict["tx_file"])
        logger.info(f"retrieved filename {self.file}")
        self.name = config_dict["name"]
        logger.info(f"creating '{self.name}' portfolio")
        self.filter_type = config_dict["filter_type"]
        self.filter_broker = config_dict["filter_broker"]
        self.funds = config_dict["funds"]
        self.delisted = config_dict["delisted"]
        self.benchmarks = config_dict["benchmarks"]
        self.other_fields = config_dict["other_fields"]
        self.transactions = self.get_transactions(
            filter_type=self.filter_type,
            filter_broker=self.filter_broker,
            other_fields=self.other_fields,
        )

        self._min_year = self.transactions["date"].min().year
        self.tickers = list(self.transactions["ticker"].unique())
        self.price_history = self._get_price_history(
            history_offline=config_dict.get("history_offline", None)
        )
        if config_dict.get("stock_splits", False):
            self.transactions = self._add_stock_splits(self.transactions)
        self.check_tx()
        self.transactions_history = self.get_transactions_history(
            tx_df=self.transactions,
            other_fields=self.other_fields,
            benchmarks=self.benchmarks,
        )
        self._max_date = self.transactions_history["date"].max()
        self.return_view = self.get_view(view="return")
        self.cost_view = self.get_view(view="cumulative_cost")

    def get_performance(self, date=None, tx_hist_df=None, lookback=None, prettify=True):
        """
        Get performance of portfolio and stocks traded at certain point of time.

        Parameters
        ----------
        date : date (default is max date)
            the date the portfolio performance should be as of.
            If none we use the max date.
        tx_hist_df : DataFrame (default is all transactions)
            dataframe to get return percent from
        lookback : int (default is None)
            the number of days to look back (uses a calendar day and not stock)
        prettify : bool (default is True)
            whether to prettify the output

        Returns
        -------
        performance : DataFrame
            the performance of individual assets as well as portfolio
                - date
                - average price
                - last price
                - cumulative units
                - cumulative cost
                - market value
                - return
                - dwrr return percentage
                - annualized dwrr return percentage
                - realized
                - unrealized
                - cumulative_dividend
                - cash
                - equity

        """
        if date is None:
            date = self._max_date
        date = pd.to_datetime(check_stock_dates(date, fix=True)["fix_tx_df"]["date"])[0]
        if date > self._max_date:
            raise ValueError(
                f"date {date} is greater than max date {self._max_date} please "
                f"provide a date less than max date."
            )

        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        tx_hist_df = tx_hist_df[tx_hist_df["date"] <= date]

        # if lookback provided only calculate performance within lookback
        if lookback is not None:
            lookback = convert_lookback(lookback)
            tx_hist_df = self._filter_lookback(
                lookback=lookback, adjust_vars=True, tx_hist_df=tx_hist_df
            )
        lookback_date = tx_hist_df["date"].min()

        return_pcts = self._get_return_pcts(date=date, tx_hist_df=tx_hist_df)

        performance = tx_hist_df.copy()
        performance["lookback_date"] = lookback_date
        performance = performance[performance["date"] == date]
        performance = performance.reset_index().set_index("ticker")
        performance = performance.drop(["index", "units", "cost"], axis=1)

        # add in portfolio metrics
        condition = performance.index.str.contains("Cash")
        performance.loc["portfolio", "cash"] = performance.loc[
            condition, "market_value"
        ].sum()

        condition = ~performance.index.str.contains("Cash|benchmark|portfolio")
        performance.loc["portfolio", "equity"] = performance.loc[
            condition, "market_value"
        ].sum()

        # check for duplicates
        duplicates = performance[performance.index.duplicated()].index
        if len(duplicates) > 0:
            logger.warning(
                f"found {len(duplicates)} duplicate tickers in performance such as "
                f"{duplicates[0]} on {date}"
            )

        performance = pd.concat([performance, return_pcts], axis=1, join="inner")

        # add in simple return percentage
        # reference to difference between simple and time weighted return
        # https://study.com/learn/lesson/time-weighted-rate-return-formula-steps-examples
        #   formula used: simple return = return / (cost - realized)
        #   cost is reduced by realized which is why we add it back in
        performance["simple_pct"] = np.where(
            (-performance["cumulative_cost"] + performance["realized"]) == 0,
            np.nan,
            performance["return"]
            / (-performance["cumulative_cost"] + performance["realized"]),
        )

        # changing format of percentage columns
        if prettify:
            pct_cols = performance.filter(like="pct").columns
            for pct_col in pct_cols:
                performance[pct_col] = performance[pct_col].apply(
                    lambda x: "{:.2%}".format(x) if x is not None else "NaN"
                )

        performance = performance[
            [
                "date",
                "lookback_date",
                "average_price",
                "last_price",
                "cumulative_units",
                "cumulative_cost",
                "market_value",
                "return",
                "dwrr_pct",
                "dwrr_ann_pct",
                "div_dwrr_pct",
                "div_dwrr_ann_pct",
                "realized",
                "unrealized",
                "cumulative_dividend",
                "cash",
                "equity",
            ]
        ]

        return performance

    def load_filename(self, tx_file):
        """
        Load transaction file.

        Parameters
        ----------
        tx_file : str
            the value to the transactions file

        Returns
        -------
        file_path : str
            the path to the transactions file

        """
        # prefix with CONFIG_PATH if that exists
        if os.path.isfile(os.path.join(config_helper.CONFIG_PATH, tx_file)):
            file_path = os.path.join(config_helper.CONFIG_PATH, tx_file)
        else:
            file_path = tx_file

        return file_path

    def get_transactions(self, filter_type=None, filter_broker=None, other_fields=None):
        """
        Get the transactions made.

        Parameters
        ----------
        filter_type : list (optional)
            list of strings to exclude out of `type` field.
            e.g. a dividend type may not want to be included in total
        filter_broker : list (optional)
            list of strings to include out of `broker` field.
        other_fields : list (optional)
            additional fields to include

        Returns
        -------
        transactions : DataFrame
            the transactions made on portfolio

        """
        if filter_type is None:
            filter_type = []
        if filter_broker is None:
            filter_broker = []
        if other_fields is None:
            other_fields = []

        try:
            if self.file.endswith(".csv"):
                transactions = pd.read_csv(self.file, parse_dates=["date"])
            elif self.file.endswith(".xlsx"):
                transactions = pd.read_excel(self.file, engine="openpyxl")
            else:
                raise ValueError(f"Unsupported file format for {self.file}")
        except FileNotFoundError as err:
            raise FileNotFoundError(f"File not found at {self.file}") from err
        except Exception as err:
            raise ValueError(f"Error loading file: {err}") from err

        logger.info(f"there are {len(transactions)} transactions in file")

        cols = ["date", "ticker", "type", "units", "cost", *other_fields]
        missing_cols = set(cols) - set(transactions.columns)
        if missing_cols:
            raise ValueError(f"Missing columns in file: {missing_cols}")

        transactions = transactions[cols]
        transactions = transactions[~transactions["type"].isin(filter_type)]
        if filter_broker:
            transactions = transactions[transactions["broker"].isin(filter_broker)]

        # raise error if length of transactions is 0
        if len(transactions) == 0:
            raise ValueError(
                "There are no transactions in file (look at if filter broker "
                f"`{filter_broker}` is correct)"
            )

        # handle multiple transactions on same day by grouping
        transactions = (
            transactions.groupby(
                by=["date", "ticker", "type", *other_fields], dropna=False
            )
            .sum()
            .reset_index()
        )

        transactions["date"] = pd.to_datetime(transactions["date"], format="%m/%d/%Y")
        transactions["date"] = convert_date_to_timezone(
            transactions["date"], timezone=None
        )

        transactions["price"] = (transactions["cost"] / transactions["units"]) * -1
        transactions.loc[transactions["ticker"] == "Cash", "price"] = 1
        transactions.loc[transactions["type"] == "DIVIDEND", "price"] = 1

        # sort values descending
        transactions = transactions.sort_values(by="date", ascending=False)

        transactions = transactions[[*cols, "price"]]

        logger.info(
            f"after filtering and grouping there are {len(transactions)} transactions "
            "in file"
        )

        return transactions

    def get_transactions_history(
        self, tx_df, price_history=None, other_fields=None, benchmarks=None
    ):
        """
        Get the history of stock transcations by merging transaction and price history.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        price_history : DataFrame
            Price history DataFrame
        other_fields : list (optional)
            additional fields to include
        benchmarks : list (optional)
            list of tickers to add as benchmarks

        Returns
        -------
        transactions_history : DataFrame
            the price history of stock transactions

        """
        if price_history is None:
            price_history = self.price_history
        if other_fields is None:
            other_fields = []
        if benchmarks is None:
            benchmarks = []

        tx_df = tx_df.copy()
        transactions = tx_df[(tx_df["cost"] != 0) | (tx_df["units"] != 0)]
        transactions = self._add_cash_tx(tx_df=transactions, other_fields=other_fields)
        transactions_history = self._add_price_history(
            tx_df=transactions, price_history=price_history, other_fields=other_fields
        )
        transactions_history = self._add_dividend(
            tx_df=transactions,
            tx_hist_df=transactions_history,
            other_fields=other_fields,
        )
        transactions_history = self._calc_tx_metrics(tx_hist_df=transactions_history)
        transactions_history = self._add_portfolio(tx_hist_df=transactions_history)

        for benchmark in benchmarks:
            benchmark_history = self._add_benchmark(
                tx_df=tx_df,
                ticker=benchmark,
                price_history=price_history,
                other_fields=other_fields,
            )
            transactions_history = pd.concat(
                [transactions_history, benchmark_history], axis=0
            )

        # sort values descending
        transactions_history = transactions_history.sort_values(
            by=["ticker", "date"], ignore_index=True, ascending=False
        )

        return transactions_history

    def get_view(self, view="market_value", tx_hist_df=None, lookback=None):
        """
        Get the a specific view of the portfolio.

        Useful for plotting returns visually.

        Parameters
        ----------
        view : str
            column to sum over on the portfolio dataframe
               - e.g. "market_value", "return", "cumulative_cost", "realized"
        tx_hist_df : DataFrame
            dataframe to get return percent from
        lookback : int (default is None)
            the number of days to look back (uses a calendar day and not stock)

        Returns
        -------
        view_df : DataFrame

        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        if lookback is not None:
            lookback = convert_lookback(lookback)
            tx_hist_df = self._filter_lookback(
                lookback=lookback, adjust_vars=True, tx_hist_df=tx_hist_df
            )
        cols = ["ticker", "date", view]
        view_df = tx_hist_df[cols]
        view_df = view_df.pivot_table(
            index="date", columns="ticker", values=view, aggfunc="sum"
        )
        view_df["portfolio"] = view_df.loc[
            :, ~view_df.columns.str.contains("benchmark|portfolio")
        ].sum(axis=1)

        return view_df

    def check_tx(self, tx_df=None):
        """
        Check that transactions have correct data.

        Parameters
        ----------
        tx_df : DataFrame
            dataframe to performe checks on

        Returns
        -------
        portfolio_checks_failed : int

        """
        if tx_df is None:
            tx_df = self.transactions.copy()

        portfolio_checks_failed = 0

        #   _______  __
        #  |_   _\ \/ /
        #    | |  \  /
        #    | |  /  \
        #    |_| /_/\_\
        #
        # Helper function to check conditions and log warnings
        def check_condition(condition, message_template, filtered_df=None):
            nonlocal portfolio_checks_failed
            if condition:
                if filtered_df:
                    message = message_template.format(
                        ticker=filtered_df.iloc[0]["ticker"],
                        units=filtered_df.iloc[0]["units"],
                        cost=filtered_df.iloc[0]["cost"],
                    )
                else:
                    message = message_template
                logger.warning(message)
                portfolio_checks_failed += 1

        # sell checks
        filtered_df = tx_df[(tx_df["type"] == "SELL") & (tx_df["units"] > 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had positive units for SELL type "
            "such as {ticker} with {units} units",
            filtered_df,
        )

        filtered_df = tx_df[(tx_df["type"] == "SELL") & (tx_df["cost"] < 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had negative cost for SELL type "
            "such as {ticker} with {cost} cost",
            filtered_df,
        )

        # sell short checks
        filtered_df = tx_df[(tx_df["type"] == "SELL SHORT") & (tx_df["units"] > 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had positive units for SELL SHORT type "
            "such as {ticker} with {units} units",
            filtered_df,
        )

        filtered_df = tx_df[(tx_df["type"] == "SELL SHORT") & (tx_df["cost"] < 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had negative cost for SELL SHORT type "
            "such as {ticker} with {cost} cost",
            filtered_df,
        )

        # buy checks
        filtered_df = tx_df[(tx_df["type"] == "BUY") & (tx_df["units"] < 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had negative units for BUY type "
            "such as {ticker} with {units} units",
            filtered_df,
        )

        filtered_df = tx_df[(tx_df["type"] == "BUY") & (tx_df["cost"] > 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had positive cost for BUY type "
            "such as {ticker} with {cost} cost",
            filtered_df,
        )

        filtered_df = tx_df[(tx_df["type"] == "BUY COVER") & (tx_df["units"] < 0)]
        # buy cover checks
        check_condition(
            not filtered_df.empty,
            "There were transactions that had negative units for BUY COVER type "
            "such as {ticker} with {units} units",
            filtered_df,
        )

        filtered_df = tx_df[(tx_df["type"] == "BUY COVER") & (tx_df["cost"] > 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had positive cost for BUY COVER type "
            "such as {ticker} with {cost} cost",
            filtered_df,
        )

        # dividend
        dividend_tx = tx_df[tx_df["type"] == "DIVIDEND"]
        filtered_df = dividend_tx[(dividend_tx["cost"] != dividend_tx["units"])]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had cost not equal to units for DIVIDEND "
            "type such as {ticker} with {units} units and {cost} cost",
            filtered_df,
        )

        filtered_df = dividend_tx[(dividend_tx["cost"] < 0)]
        check_condition(
            not filtered_df.empty,
            "There were transactions that had cost less than 0 for DIVIDEND "
            "type such as {ticker} with {units} units",
            filtered_df,
        )

        # broker check
        brokers_allowed = 2  # there can be 2 brokers, nan and the filtered broker
        check_condition(
            (
                "broker" in tx_df.columns
                and len(tx_df["broker"].unique()) > brokers_allowed
            ),
            "If using broker column the broker should be unique or else the "
            "the grouping of transactions will be incorrect. ",
        )

        #   _______   ______  _____
        #  |_   _\ \ / /  _ \| ____|
        #    | |  \ V /| |_) |  _|
        #    | |   | | |  __/| |___
        #    |_|   |_| |_|   |_____|
        #
        tx_allowed_types = [
            "BOOK",
            "BUY",
            "Cash",
            "SELL",
            "BUY COVER",
            "SELL SHORT",
            "DIVIDEND",
        ]
        tx_types = tx_df["type"].unique()
        for tx_type in tx_types:
            if tx_type not in tx_allowed_types:
                logger.warning(f"This type '{tx_type}' is not in {tx_allowed_types}")
                portfolio_checks_failed = portfolio_checks_failed + 1

        #    ____ ___  _    _   _ __  __ _   _
        #   / ___/ _ \| |  | | | |  \/  | \ | |
        #  | |  | | | | |  | | | | |\/| |  \| |
        #  | |__| |_| | |__| |_| | |  | | |\  |
        #   \____\___/|_____\___/|_|  |_|_| \_|
        #
        tx_needed_columns = ["ticker", "date", "type", "units", "cost"]
        tx_columns = list(tx_df.columns)
        for tx_needed_column in tx_needed_columns:
            check_condition(
                tx_needed_column not in tx_columns,
                f"This column '{tx_needed_column}' is needed, and not in {tx_columns}",
            )

        #   ____    _  _____ _____
        #  |  _ \  / \|_   _| ____|
        #  | | | |/ _ \ | | |  _|
        #  | |_| / ___ \| | | |___
        #  |____/_/   \_\_| |_____|
        #
        invalid_dt = check_stock_dates(tx_df, fix=False)["invalid_dt"]
        check_condition(len(invalid_dt) > 0, "Invalid dates found in transactions")

        return portfolio_checks_failed

    def _get_price_history(self, history_offline=None):
        """
        Get the history of prices.

        Parameters
        ----------
        offline_location : str (optional)
            location of the csv price history. This is useful when not connected
            to internet and the price history is already available.
        history_offline : str (optional)
            location of the csv price history. This is useful when not connected
            to internet and the price history is already available.

        Returns
        -------
        price_history : DataFrame
            the price history
               - ticker
               - date
               - last price

        """
        if history_offline:
            try:
                if history_offline.endswith(".csv"):
                    price_history = pd.read_csv(
                        history_offline, index_col=0, parse_dates=["date"]
                    )
                else:
                    raise ValueError("Unsupported file format needs to be .csv")
            except FileNotFoundError as err:
                raise FileNotFoundError(f"File not found at {history_offline}") from err
            except Exception as err:
                raise ValueError(f"Error loading file: {err}") from err

            return price_history

        # if price history isn't offline, download from yahoo finance
        logger.info("Downloading price history from yahoo finance")
        tickers = [
            tick
            for tick in self.tickers
            if tick not in self.funds + self.delisted + ["Cash"]
        ] + self.benchmarks

        if self.benchmarks:
            logger.info(f"Adding {self.benchmarks} as a benchmark")

        wrapper = Yahoo()
        price_history = wrapper.stock_history(tickers=tickers, min_year=self._min_year)

        # adding fund price history
        transactions = self.transactions
        template_df = pd.DataFrame(price_history["date"].unique(), columns=["date"])
        funds = [tick for tick in self.tickers if tick in self.funds]
        delisted = [tick for tick in self.tickers if tick in self.delisted]
        if funds:
            logger.info(
                f"Did not get price info for {funds} and will use transaction"
                " price to develop price history, since they are funds and not"
                " available in stock exchanges"
            )
        if delisted:
            logger.info(
                f"Did not get price info for {delisted} and will use transaction"
                " price to develop price history, since they are delisted and not"
                " available in stock exchanges"
            )

        # add price history for funds and delisted
        all_funds = funds + delisted
        if all_funds:
            fund_dfs = [
                transactions[transactions["ticker"] == fund] for fund in all_funds
            ]
            all_funds_df = pd.concat(fund_dfs)

            expanded_template_df = pd.MultiIndex.from_product(
                [template_df["date"], all_funds], names=["date", "ticker"]
            ).to_frame(index=False)

            fund_hist_df = pd.merge(
                expanded_template_df,
                all_funds_df[["date", "ticker", "price"]],
                how="outer",
                on=["date", "ticker"],
            )

            fund_hist_df = fund_hist_df.groupby(["date", "ticker"]).min().reset_index()
            fund_hist_df[["price"]] = fund_hist_df.groupby("ticker")[["price"]].ffill()
            fund_hist_df = fund_hist_df.rename(columns={"price": "last_price"})
            price_history = pd.concat([price_history, fund_hist_df])

        # adding ticker `Cash` for price history lookup
        if "Cash" in self.tickers:
            logger.info("Adding transaction history for cash transactions")
            df = template_df.copy()
            df["ticker"] = "Cash"
            df["last_price"] = 1
            price_history = pd.concat([price_history, df], axis=0)

        # sort values descending
        price_history = price_history.sort_values(["ticker", "date"], ascending=False)

        # add in stock splits
        price_history["stock_splits"] = price_history["stock_splits"].replace(0, 1)
        price_history["cumulative_stock_splits"] = price_history.groupby("ticker")[
            "stock_splits"
        ].cumprod()

        # check if there are any missing values for a ticker in price history
        pivot = price_history.pivot(index="date", columns="ticker", values="last_price")
        for tick in tickers:
            check = pivot[tick]
            check = check[check.index >= check.first_valid_index()]
            missing_dates = check[check.isnull()].index
            if not missing_dates.empty:
                logger.warning(
                    f"Missing price history for {tick},"
                    f" first noticed on {missing_dates[0]}."
                    " Most likely the ticker is delisted or not available in"
                    " stock exchanges."
                )

        return price_history

    def _add_price_history(self, tx_df, price_history=None, other_fields=None):
        """
        Add price history to transactions DataFrame.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        price_history : DataFrame
            Price history DataFrame
        other_fields : list (optional)
            additional fields to include

        Returns
        -------
        tx_hist_df : DataFrame
            DataFrame that has transactions and price history

        """
        if other_fields is None:
            other_fields = []

        # remove dividend transactions
        tx_df = tx_df[tx_df["type"] != "DIVIDEND"].copy()

        tickers = list(tx_df["ticker"].unique())

        tx_df = (
            tx_df.groupby(by=["date", "ticker", *other_fields])
            .sum(numeric_only=True)
            .reset_index()
        )

        tx_df["price"] = np.where(
            tx_df["units"] == 0,
            0,
            tx_df["cost"] / tx_df["units"] * -1,
        )

        price_history = price_history[price_history["ticker"].isin(tickers)]

        tx_hist_df = pd.merge(
            price_history,
            tx_df[["date", "ticker", "price", "units", "cost", *other_fields]],
            how="outer",
            on=["date", "ticker"],
        ).sort_values(by=["ticker", "date"], ignore_index=True)

        # fill in acquisition ticker prices
        tx_hist_df["last_price"] = np.where(
            (tx_hist_df["price"] != 0) & (tx_hist_df["last_price"] == 0),
            tx_hist_df["price"],
            tx_hist_df["last_price"],
        )
        tx_hist_df["last_price"] = tx_hist_df.groupby("ticker")["last_price"].ffill()
        tx_hist_df = tx_hist_df.fillna(0)

        # sort values descending
        tx_hist_df = tx_hist_df.sort_values(by="date", ascending=False)

        # fill in missing other_fields values
        for field in other_fields:
            tx_hist_df[field] = tx_hist_df[field].replace(0, np.nan)
            tx_hist_df[field] = tx_hist_df[field].ffill().bfill()

        return tx_hist_df

    def _add_cash_tx(self, tx_df, other_fields=None):
        """
        Add cash transactions to transactions DataFrame.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        other_fields : list (optional)
            additional fields to include

        Returns
        -------
        tx_df : DataFrame
            DataFrame that has cash included

        """
        if other_fields is None:
            other_fields = []

        tickers = list(tx_df["ticker"].unique())

        # create cash transactions from stock purchases
        if "Cash" in tickers:
            non_cash_tx = tx_df[tx_df["ticker"] != "Cash"].copy()
            non_cash_tx["ticker"] = "Cash"
            non_cash_tx["type"] = "Cash"
            non_cash_tx["units"] = non_cash_tx["cost"]
            non_cash_tx["price"] = 1
            tx_df = pd.concat([tx_df, non_cash_tx], axis=0)

        # cash dividends are treated as interest and not a cost
        # but adds to units and market value
        cash_div_tx = tx_df[
            (tx_df["ticker"] == "Cash") & (tx_df["type"] == "DIVIDEND")
        ].copy()
        if not cash_div_tx.empty:
            cash_div_tx["type"] = "Cash"
            cash_div_tx["cost"] = 0
            tx_df = pd.concat([tx_df, cash_div_tx], axis=0)

        # the cash transactions cost is opposite to equity except for
        # cash dividends which will act as interest
        condition = (tx_df["ticker"] == "Cash") & (tx_df["type"] != "DIVIDEND")
        tx_df.loc[condition, "cost"] *= -1

        return tx_df

    def _add_stock_splits(self, tx_df, price_history=None):
        """
        Add stock splits to transactions.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate splits on
        price_history : DataFrame
            Price history DataFrame

        Returns
        -------
        tx_df : DataFrame
            DataFrame that has adjusted transactions for splits

        """
        if price_history is None:
            price_history = self.price_history

        # get the split adjustments
        tx_df = pd.merge(
            tx_df,
            price_history[["date", "ticker", "cumulative_stock_splits"]],
            on=["date", "ticker"],
            how="left",
        )
        tx_df["cumulative_stock_splits"] = tx_df["cumulative_stock_splits"].fillna(1)

        # get the tickers that had adjustments
        adjusted_ticks = tx_df[tx_df["cumulative_stock_splits"] != 1]["ticker"].unique()

        # adjust the transactions
        logger.info(
            f"Adjusted the following tickers for stock splits: {adjusted_ticks}"
        )
        tx_df["units"] = np.where(
            tx_df["type"] != "DIVIDEND",
            tx_df["units"] * tx_df["cumulative_stock_splits"],
            tx_df["units"],
        )

        tx_df = tx_df.sort_values(by="date", ascending=False)

        return tx_df

    def _add_dividend(self, tx_df, tx_hist_df, other_fields=None):
        """
        Add dividend column to transactions history DataFrame.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to get dividends from
        tx_hist_df : DataFrame
            Transactions history to add dividends to
        other_fields : list (optional)
            additional fields to include

        Returns
        -------
        tx_hist_df : DataFrame
            DataFrame that has dividend column included

        """
        if other_fields is None:
            other_fields = []

        dividends = tx_df[tx_df["type"] == "DIVIDEND"]

        dividends = (
            dividends.groupby(by=["date", "ticker", *other_fields])
            .sum(numeric_only=True)
            .reset_index()
        )
        dividends = dividends.rename(columns={"cost": "dividend"})

        # cash dividends are treated as interest
        dividends.loc[dividends["ticker"] == "Cash", "dividend"] = 0

        if dividends.empty:
            logger.info("There are no dividends added to portfolio")
        else:
            logger.info(
                f"Adding {dividends['dividend'].sum()} of dividends to portfolio"
            )

        tx_hist_df = pd.merge(
            tx_hist_df,
            dividends[["date", "ticker", "dividend"]],
            on=["date", "ticker"],
            how="left",
        )
        tx_hist_df["dividend"] = tx_hist_df["dividend"].fillna(0)

        return tx_hist_df

    def _calc_tx_metrics(self, tx_hist_df):
        """
        Calculate summation metrics on transactions DataFrame.

        Note:
        does not include metrics for entire 'portfolio' but only for each ticker

        Parameters
        ----------
        tx_hist_df : DataFrame
            Transactions history to calculate metrics on

        Returns
        -------
        transaction_metrics : DataFrame
            DataFrame containing updated metrics
            - cumulative_units
            - cumulative_cost
            - average_price
            - market_value
            - return
            - unrealized
            - realized
            - cumulative_dividend

        """
        # sort values ascending to calculate cumsum correctly
        tx_hist_df = tx_hist_df.sort_values(by=["ticker", "date"], ascending=True)

        # cumulative amounts
        tx_hist_df["cumulative_units"] = tx_hist_df.groupby("ticker")[
            "units"
        ].transform(pd.Series.cumsum)
        tx_hist_df["cumulative_cost_without_dividend"] = tx_hist_df.groupby("ticker")[
            "cost"
        ].transform(pd.Series.cumsum)
        tx_hist_df["cumulative_dividend"] = tx_hist_df.groupby("ticker")[
            "dividend"
        ].transform(pd.Series.cumsum)
        # adding dividends profit to cumulative cost
        tx_hist_df["cumulative_cost"] = (
            tx_hist_df["cumulative_cost_without_dividend"]
            + tx_hist_df["cumulative_dividend"]
        )

        # average price
        tx_hist_df = tx_hist_df.groupby("ticker", group_keys=False).apply(
            self._calc_average_price_speed
        )

        tx_hist_df.loc[tx_hist_df["ticker"] == "Cash", "average_price"] = 1

        # market value
        tx_hist_df["market_value"] = (
            tx_hist_df["cumulative_units"] * tx_hist_df["last_price"]
        )

        # return
        tx_hist_df["return"] = (
            tx_hist_df["market_value"] + tx_hist_df["cumulative_cost"]
        )

        tx_hist_df["unrealized"] = tx_hist_df["market_value"] - (
            tx_hist_df["average_price"] * tx_hist_df["cumulative_units"]
        )

        tx_hist_df["realized"] = (
            tx_hist_df["return"]
            - tx_hist_df["unrealized"]
            - tx_hist_df["cumulative_dividend"]
        )

        # fill in zeroes
        for field in [
            "average_price",
            "market_value",
            "return",
            "unrealized",
            "realized",
            "cumulative_dividend",
            "cumulative_units",
        ]:
            condition = (tx_hist_df["cumulative_cost"] == 0) & (
                tx_hist_df["dividend"] == 0
            )
            tx_hist_df.loc[condition, field] = tx_hist_df.loc[condition, field].replace(
                0, np.nan
            )

        tx_hist_df.loc[tx_hist_df["dividend"] == 0, "cumulative_cost"] = tx_hist_df[
            "cumulative_cost"
        ].replace(0, np.nan)

        transaction_metrics = tx_hist_df

        return transaction_metrics

    def _add_benchmark(self, tx_df, ticker, price_history=None, other_fields=None):
        """
        Add a benchmark with transaction history dataframe.

        Notes
        -----
        Benchmark does not include any dividends from the benchmark, but
        does include investing dividends from portfolio

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        ticker : str
            The ticker to create the benchmark for
        price_history : DataFrame
            Price history DataFrame
        other_fields : list (optional)
            additional fields to include

        Returns
        -------
        benchmark_tx_hist : DataFrame
            DataFrame containing transaction history for dataframe

        """
        if other_fields is None:
            other_fields = []
        if price_history is None:
            price_history = self.price_history

        tx_df = tx_df.copy()
        transactions = tx_df[(tx_df["cost"] != 0) | (tx_df["units"] != 0)]
        benchmark_tx = transactions[transactions["ticker"] == "Cash"].copy()
        if benchmark_tx.empty:
            logger.warning(
                "There were no transactions in benchmark. Please include cash "
                "transactions"
            )

        # add benchmark from cash transactions
        benchmark_tx["ticker"] = ticker
        benchmark_tx["cost"] = -benchmark_tx["cost"]

        benchmark_tx = (
            benchmark_tx.groupby(by=["date", "ticker", *other_fields])
            .sum(numeric_only=True)
            .reset_index()
        )

        benchmark_tx["price"] = np.where(
            benchmark_tx["units"] == 0,
            0,
            benchmark_tx["cost"] / benchmark_tx["units"] * -1,
        )

        # assuming that there are 0 dividends from benchmark
        benchmark_tx["dividend"] = 0

        price_history = price_history[price_history["ticker"] == ticker]

        benchmark_tx_hist = (
            pd.merge(
                price_history,
                benchmark_tx[
                    [
                        "date",
                        "ticker",
                        "price",
                        "units",
                        "cost",
                        "dividend",
                        *other_fields,
                    ]
                ],
                how="outer",
                on=["date", "ticker"],
            )
            .fillna(0)
            .sort_values(by=["ticker", "date"], ignore_index=True)
        )

        # zero out sale price of offsetting transactions
        condition = benchmark_tx_hist["units"] == 0
        benchmark_tx_hist.loc[condition, "price"] = 0
        # update sale price
        condition = benchmark_tx_hist["units"] != 0
        benchmark_tx_hist.loc[condition, "price"] = benchmark_tx_hist.loc[
            condition, "last_price"
        ]
        # update units
        benchmark_tx_hist.loc[condition, "units"] = -(
            benchmark_tx_hist.loc[condition, "cost"]
            / benchmark_tx_hist.loc[condition, "last_price"]
        )

        # fill in other_fields null values
        for field in other_fields:
            benchmark_tx_hist[field] = benchmark_tx_hist[field].replace(0, np.nan)
            benchmark_tx_hist[field] = benchmark_tx_hist.groupby(
                ["ticker"], group_keys=False
            )[field].apply(lambda x: x.ffill().bfill())

        # sort values descending
        benchmark_tx_hist = benchmark_tx_hist.sort_values(
            by=["ticker", "date"], ascending=False
        )
        benchmark_tx_hist["ticker"] = "benchmark-" + ticker

        benchmark_tx_hist = self._calc_tx_metrics(benchmark_tx_hist)

        return benchmark_tx_hist

    def _add_portfolio(self, tx_hist_df=None):
        """
        Add the portfolio with transaction history dataframe.

        Parameters
        ----------
        tx_hist_df : DataFrame
            Transactions history

        Returns
        -------
        portfolio_tx_hist : DataFrame
            DataFrame containing portfolio transaction history

        """
        portfolio_tx_hist = pd.DataFrame()
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        views = [
            "cost",
            "cumulative_cost",
            "cumulative_cost_without_dividend",
            "market_value",
            "return",
            "unrealized",
            "realized",
            "dividend",
            "cumulative_dividend",
        ]
        for view in views:
            cols = ["ticker", "date", view]
            view_df = tx_hist_df[cols]
            view_df = view_df.pivot_table(
                index="date", columns="ticker", values=view, aggfunc="sum"
            )
            view_df["portfolio"] = view_df.loc[
                :, ~view_df.columns.str.contains("benchmark")
            ].sum(axis=1)
            portfolio_tx_hist[view] = view_df["portfolio"]
        portfolio_tx_hist["ticker"] = "portfolio"
        portfolio_tx_hist = portfolio_tx_hist.reset_index()
        portfolio_tx_hist = pd.concat([tx_hist_df, portfolio_tx_hist], axis=0)

        return portfolio_tx_hist

    def _calc_average_price(self, df):
        """
        Calculate the average cost basis.

        Parameters
        ----------
        df : DataFrame
            dataframe to apply calculation to

        Returns
        -------
        df : DataFrame
            dataframe that includes the "average price"

        """
        df.loc[df.index[0], "average_price"] = df.loc[df.index[0], "price"]
        if len(df) != 1:
            for i in range(1, len(df)):
                if df.loc[df.index[i], "cumulative_units"] == 0:
                    df.loc[df.index[i], "average_price"] = 0
                elif df.loc[df.index[i], "units"] <= 0:
                    df.loc[df.index[i], "average_price"] = df.loc[
                        df.index[i - 1], "average_price"
                    ]
                else:
                    df.loc[df.index[i], "average_price"] = (
                        df.loc[df.index[i], "price"] * df.loc[df.index[i], "units"]
                        + df.loc[df.index[i - 1], "cumulative_units"]
                        * df.loc[df.index[i - 1], "average_price"]
                    ) / df.loc[df.index[i], "cumulative_units"]
        return df

    def _calc_average_price_speed(self, df):
        """
        Calculate the average cost basis.

        Parameters
        ----------
        df : DataFrame
            dataframe to apply calculation to

        Returns
        -------
        df : DataFrame
            dataframe that includes the "average price"

        """
        df["average_price"] = np.nan
        tx = df[df["units"] != 0]
        if len(tx) != 0:
            tx.loc[tx.index[0], "average_price"] = tx.loc[tx.index[0], "price"]
        if len(tx) != 1:
            for i in range(1, len(tx)):
                if tx.loc[tx.index[i], "cumulative_units"] == 0:
                    tx.loc[tx.index[i], "average_price"] = 0
                elif tx.loc[tx.index[i], "units"] <= 0:
                    tx.loc[tx.index[i], "average_price"] = tx.loc[
                        tx.index[i - 1], "average_price"
                    ]
                else:
                    tx.loc[tx.index[i], "average_price"] = (
                        tx.loc[tx.index[i], "price"] * tx.loc[tx.index[i], "units"]
                        + tx.loc[tx.index[i - 1], "cumulative_units"]
                        * tx.loc[tx.index[i - 1], "average_price"]
                    ) / tx.loc[tx.index[i], "cumulative_units"]

        # merge average prices back into df
        df.update(tx["average_price"])
        df["average_price"] = df["average_price"].ffill()
        df.loc[df["cumulative_units"] == 0, "average_price"] = 0
        return df

    def _get_return_pct(
        self, ticker, date, tx_hist_df=None, lookback=None, debug=False
    ):
        """
        Get the dollar and time weighted return of a ticker.

        TODO same day transactions do mess up the calculation of returns

        Notes
        -----
           Dollar Weighted Return (DWRR)
             This is annualized
             Using the xirr function to calculate dwrr
             https://anexen.github.io/pyxirr/functions.html#xirr
             https://www.investopedia.com/terms/m/money-weighted-return.asp
             Formula is:
             CF0 + CF1 / (1 + r)^1 + CF2 / (1 + r)^2 + ... + CFn / (1 + r)^n = 0

           Modified Dietz Return (MDRR)
              This is non-annualized
              Using the formula from wikipedia
              https://en.wikipedia.org/wiki/Modified_Dietz_method
              Formula is:
              (end_value - start_value - cash_flows) /
              (start_value + time_weighted_cash_flows)

           Time Weighted Return (TWRR)
              TODO - although not a big fan as it doesn't take into account cash flows
              This is non-annualized
              Using the formula from investopedia
              https://www.investopedia.com/terms/t/time-weightedror.asp
              Formula is:
              (1 + r1) * (1 + r2) * ... * (1 + rn) - 1

        Parameters
        ----------
        ticker : str
            ticker that will be used to calculate metric
        date : date
            date on which to perform the returns as of
        tx_hist_df : DataFrame (optional)
            stock dataframe to get return percent from
        lookback : int (optional)
            the number of days to look back (uses a calendar day and not stock)
        debug : bool (optional)
            if True, then will return the transactions used to calculate the return

        Returns
        -------
        return_dict : dict
            dictionary of returns

        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history

        tx_hist_df = tx_hist_df[tx_hist_df["date"] <= date]

        # if lookback provided then filter history to only include that period
        if lookback is not None:
            lookback = convert_lookback(lookback)
            tx_hist_df = self._filter_lookback(
                lookback=lookback, adjust_vars=False, tx_hist_df=tx_hist_df
            )

        # start the dataframe at the first market value for ticker
        ticker_df = tx_hist_df[tx_hist_df["ticker"] == ticker]
        if ticker_df["market_value"].sum() == 0:
            ticker_begin = 0
        else:
            ticker_begin = ticker_df[
                (ticker_df["market_value"].notna()) & (ticker_df["market_value"] != 0)
            ].index[-1]
        ticker_df = ticker_df.loc[ticker_df.index <= ticker_begin]

        # get the entry price, transactions, current price
        entry_price = ticker_df[ticker_df["date"] == ticker_df["date"].min()].copy()
        ticker_transactions = ticker_df[
            (ticker_df["date"] > ticker_df["date"].min())
            & (ticker_df["date"] <= date)
            & ((ticker_df["cost"] != 0) | (ticker_df["dividend"] != 0))
        ].copy()
        current_price = ticker_df[(ticker_df["date"] == date)].copy()

        # create the return transactions that will have positive and negative
        # values.
        #
        # The return is based on
        #   - an intitial investment (entry price) net an return,
        #   - transactions (ticker_transactions),
        #   - finally the current market price which includes the dividend. Cash
        #     excludes dividend since that is already in market value
        #
        # the dividend return is based on
        #   - an intitial investment (entry price) not including dividend return,
        #   - transactions (ticker_transactions),
        #   - finally the current market price which includes the dividend return.
        #     Cash excludes dividend since that is already in cost

        # equity + dividend
        entry_price["return_txs"] = np.where(
            entry_price["units"]
            == entry_price["cumulative_units"],  # initial investment should use cost
            entry_price["cumulative_cost"],
            -entry_price["market_value"],
        )
        ticker_transactions["return_txs"] = ticker_transactions["cost"]
        current_price["return_txs"] = (
            current_price["market_value"] + current_price["cumulative_dividend"]
        )

        # only dividend
        entry_price["return_div_txs"] = np.where(
            entry_price["cost"] == 0,
            entry_price["cumulative_cost_without_dividend"]
            - entry_price["cumulative_dividend"],
            entry_price["cumulative_cost"],
        )
        ticker_transactions["return_div_txs"] = ticker_transactions["cost"]
        current_price["return_div_txs"] = (
            -current_price["cumulative_cost_without_dividend"]
            + current_price["cumulative_dividend"]
        )

        # combine the transactions
        return_transactions = pd.concat(
            [entry_price, ticker_transactions, current_price], ignore_index=True
        ).sort_values(by="date", ascending=False)
        return_transactions["return_txs"] = return_transactions["return_txs"].replace(
            np.nan, 0
        )
        return_transactions["return_div_txs"] = return_transactions[
            "return_div_txs"
        ].replace(np.nan, 0)

        # makes sure that ticker had transactions both negative
        # and positive to calculate return
        dwrr_return_pct = np.NaN
        dwrr_ann_return_pct = np.NaN
        dwrr_div_return_pct = np.NaN
        dwrr_div_ann_return_pct = np.NaN
        mdrr_return_pct = np.NaN
        mdrr_ann_return_pct = np.NaN
        if return_transactions.empty:
            logger.debug(
                f"There were no transactions for {ticker} to calculate the return"
            )

        elif (
            len(return_transactions) == 1
            and return_transactions["return_txs"].iloc[0] == 0
        ):
            logger.debug(
                f"The ticker {ticker} is in portfolio but has no transactions"
                " to calculate the return"
            )

        elif (
            not min(return_transactions["return_txs"])
            < 0
            < max(return_transactions["return_txs"])
        ):
            logger.warning(
                f"The transactions for {ticker} with preformance date `{date}` "
                f" did not have positive and negatives with "
                f"minimum of `{min(return_transactions['return_txs'])}` and "
                f"maximum of `{max(return_transactions['return_txs'])}`"
            )

        elif not min(return_transactions["return_div_txs"]) < 0 < max(
            return_transactions["return_div_txs"]
        ) and not all(return_transactions["return_div_txs"] == 0):
            logger.warning(
                f"The transactions for {ticker} did not have positive and "
                f"negative transactions for dividends"
            )

        else:
            # for annualizing returns need the days
            start_date = return_transactions["date"].iloc[-1]
            end_date = return_transactions["date"].iloc[0]
            days = (end_date - start_date).days

            # the annual percentage can be high when the days are low
            # e.g. 2% return in 1 day is greater than 1000 annualized
            # e.g. 10% return in 1 day is greater than 1e15 annualized
            max_percentage = 1e20

            # calculating the dwrr return
            # ---------------------------
            dwrr_ann_return_pct = xirr(
                return_transactions["date"], return_transactions["return_txs"]
            )
            # where dwrr can't be calculated
            if dwrr_ann_return_pct is None:
                logger.warning(
                    f"DWRR return for {ticker} is None likely due to percentage "
                    f"too high (or low) fall back with simple return"
                )
                dwrr_return_pct = (
                    -return_transactions["return_txs"].iloc[0]
                    - return_transactions["return_txs"].iloc[-1]
                ) / return_transactions["return_txs"].iloc[-1]
                dwrr_ann_return_pct = np.NaN
            elif dwrr_ann_return_pct > max_percentage:
                logger.warning(
                    f"DWRR return for {ticker} is greater than {max_percentage}%"
                )
                dwrr_return_pct = (1 + dwrr_ann_return_pct) ** (days / 365) - 1
                dwrr_ann_return_pct = np.NaN
            else:
                dwrr_return_pct = (1 + dwrr_ann_return_pct) ** (days / 365) - 1

            # calculating the dwrr return for dividends
            # -----------------------------------------
            dwrr_div_ann_return_pct = xirr(
                return_transactions["date"], return_transactions["return_div_txs"]
            )
            # where dwrr can't be calculated
            if dwrr_div_ann_return_pct is None:
                pass
            elif dwrr_div_ann_return_pct > max_percentage:
                logger.warning(
                    f"DWRR div return for {ticker} is greater than {max_percentage}%"
                )
                dwrr_div_return_pct = (1 + dwrr_div_ann_return_pct) ** (days / 365) - 1
                dwrr_div_ann_return_pct = np.NaN
            else:
                dwrr_div_return_pct = (1 + dwrr_div_ann_return_pct) ** (days / 365) - 1

            # calculating the dietz return
            # ----------------------------
            return_transactions["weight"] = (
                days - (return_transactions["date"] - start_date).dt.days
            ) / (days)
            return_transactions["weighted_value"] = (
                return_transactions["return_txs"] * return_transactions["weight"]
            )
            mdrr_return_pct = return_transactions["return_txs"].sum() / (
                return_transactions["weighted_value"].sum() * -1
            )
            # where mdrr can't be calculated
            if mdrr_return_pct is None:
                pass
            elif mdrr_return_pct > max_percentage:
                pass
            elif mdrr_return_pct < -1:
                pass
            else:
                mdrr_ann_return_pct = (1 + mdrr_return_pct) ** (365 / days) - 1

        return_dict = {}
        return_dict["dwrr_return_pct"] = dwrr_return_pct
        return_dict["dwrr_ann_return_pct"] = dwrr_ann_return_pct
        return_dict["div_dwrr_return_pct"] = dwrr_div_return_pct
        return_dict["div_dwrr_ann_return_pct"] = dwrr_div_ann_return_pct
        return_dict["mdrr_return_pct"] = mdrr_return_pct
        return_dict["mdrr_ann_return_pct"] = mdrr_ann_return_pct

        if debug:
            return_dict["return_transactions"] = return_transactions

        return return_dict

    def _get_return_pcts(self, date=None, tx_hist_df=None, lookback=None):
        """
        Get the dollar weighted return of transactions.

        Parameters
        ----------
        date : date (optional)
            date on which to perform the returns as of
        tx_hist_df : DataFrame (optional)
            dataframe to get return percent from
        lookback : int (optional)
            the number of days to look back (uses a calendar day and not stock)

        Returns
        -------
        return_pcts : DataFrame
            returns of all transactions

        """
        if date is None:
            date = self._max_date
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        if lookback is not None:
            lookback = convert_lookback(lookback)

        tickers = list(tx_hist_df["ticker"].unique())

        return_data_list = []  # a list to collect data dictionaries

        # get return of each ticker
        for ticker in tickers:
            return_dict = self._get_return_pct(
                ticker=ticker,
                date=date,
                tx_hist_df=tx_hist_df,
                lookback=lookback,
            )

            filtered_return_dict = {
                "ticker": ticker,
                "dwrr_pct": return_dict["dwrr_return_pct"],
                "dwrr_ann_pct": return_dict["dwrr_ann_return_pct"],
                "div_dwrr_pct": return_dict["div_dwrr_return_pct"],
                "div_dwrr_ann_pct": return_dict["div_dwrr_ann_return_pct"],
            }
            return_data_list.append(filtered_return_dict)

        return_pcts = pd.DataFrame(return_data_list)
        return_pcts = return_pcts.set_index(["ticker"])

        return return_pcts

    def _filter_lookback(self, lookback, adjust_vars=False, tx_hist_df=None):
        """
        Modify the transactions history dataframe to only include lookback.

        Parameters
        ----------
        lookback : int
            the number of days to look back (uses a calendar day and not stock)
        adjust_vars : bool
            whether to adjust the variables return, realized, unrealized, and dividend
        tx_hist_df : DataFrame (optional)
            stock dataframe to get return percent from

        Returns
        -------
        lookback_df : DataFrame
            dataframe that includes the lookback period

        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        lookback = convert_lookback(lookback)
        lookback_df = tx_hist_df.copy()

        # Using calendar lookback, but getting closest trading day
        end_date = lookback_df["date"].max()
        cal_start_date = end_date - timedelta(days=lookback)
        buffer_date = cal_start_date - timedelta(days=7)
        stock_dates = (
            mcal.get_calendar("NYSE")
            .schedule(start_date=buffer_date, end_date=end_date)
            .index
        )
        start_date = max([date for date in stock_dates if date <= cal_start_date])
        lookback_df = lookback_df[lookback_df["date"] >= start_date]

        if adjust_vars:
            # List of variables to modify
            variables = ["return", "unrealized", "realized", "cumulative_dividend"]

            # Grouping the DataFrame by 'ticker' and applying the operation to
            # each group that will subtract the prior value from the current value.
            for variable in variables:
                lookback_df[variable] = (
                    lookback_df.groupby("ticker")[variable]
                    .transform(
                        lambda x: np.nan
                        if x.dropna().empty
                        else x - x.loc[x.last_valid_index()]
                    )
                    .fillna(0)
                )

        return lookback_df


class Manager:
    """
    Manager is a class that analyzes multiple portfolios.

    Parameters
    ----------
    config_path : str
        path to the portfolio file
    portfolios : list (default is None)
        list of portfolios in the Portfolio class to analyze.

    """

    def __init__(
        self,
        config_path,
        portfolios=None,
    ):
        """Initialize the Manager class."""
        # create list of portfolios in configuration
        if portfolios is None:
            sections = config_helper.get_config(config_path).sections()
            portfolios = [item for item in sections if item != "static"]

        self.portfolios = [
            Portfolio(config_path=config_path, portfolio=item) for item in portfolios
        ]

    def get_summary(self, date=None, lookbacks=None):
        """
        Get summary of portfolios.

        Parameters
        ----------
        date : date
            the date the asset summary should be as of.
            If none we use the max date.
        lookbacks : list (default is None)
            the number of days to look back

        Returns
        -------
        summary : DataFrame
            the summary of portfolios
                - cash
                - equity
                - market value
                - return
                - benchmark return

        """
        if lookbacks is None:
            lookbacks = [None]
        elif isinstance(lookbacks, int):
            lookbacks = [lookbacks]
        portfolio_repr = ", ".join([portfolio.name for portfolio in self.portfolios])
        logger.info(
            f"Summarizing following portfolios: [{portfolio_repr}] "
            f"with lookbacks {lookbacks}"
        )

        for i, lookback in enumerate(lookbacks):
            converted_lookback = convert_lookback(lookback)
            pfs = []
            # getting summary of each portfolio
            for portfolio in self.portfolios:
                performance = portfolio.get_performance(
                    date=date, lookback=converted_lookback
                )
                pf = performance[performance.index == "portfolio"].rename(
                    index={"portfolio": portfolio.name}
                )
                pf = pf.rename(
                    columns={"dwrr_pct": str(converted_lookback) + "_dwrr_pct"}
                )
                pf = pf.rename(
                    columns={"div_dwrr_pct": str(converted_lookback) + "_div_dwrr_pct"}
                )
                # adding benchmark to the summary
                benchmark = performance[
                    performance.index.str.contains("benchmark")
                ].head(1)
                benchmark_dict = {}
                if not benchmark.empty:
                    benchmark_dict["benchmark"] = benchmark.index.values[0].split("-")[
                        1
                    ]
                    benchmark_dict[str(converted_lookback) + "_benchmark_dwrr_pct"] = (
                        benchmark["dwrr_pct"].values[0]
                    )

                pf = pf.assign(**benchmark_dict)
                pfs.append(pf)

            # dataframe prepare (drop, reorder, format)
            summary = pd.concat(pfs)
            if i == 0:
                columns_to_keep = [
                    "date",
                    "lookback_date",
                    "market_value",
                    "equity",
                    "cash",
                    "cumulative_cost",
                    "return",
                    "realized",
                    "unrealized",
                    "cumulative_dividend",
                    "benchmark",
                ]
                columns_to_keep += summary.filter(like="_dwrr_pct").columns.tolist()
                summary = summary.drop(
                    summary.columns.difference(columns_to_keep), axis=1
                )
                summary = summary.loc[:, columns_to_keep]
                summary_all = summary.copy()
            else:
                columns_to_keep = summary.filter(like="_dwrr_pct").columns.tolist()
                summary = summary.drop(
                    summary.columns.difference(columns_to_keep), axis=1
                )
                summary = summary.loc[:, columns_to_keep]
                summary_all = pd.merge(
                    summary_all, summary, how="left", left_index=True, right_index=True
                )

        return summary_all

    def get_view(self, view="market_value"):
        """
        Get the view of portfolios.

        Useful for plotting returns visually.

        Parameters
        ----------
        view : str
            column to sum over on the portfolio dataframe
               - e.g. "market_value", "return", "cumulative_cost", "realized"

        Returns
        -------
        view_df : DataFrame

        """
        portfolio_repr = ", ".join([portfolio.name for portfolio in self.portfolios])
        logger.info(f"View of following portfolios: [{portfolio_repr}]")
        dfs = []
        for portfolio in self.portfolios:
            df = portfolio.get_view(view=view)
            df = df[["portfolio"]]
            df = df.rename(columns={"portfolio": portfolio.name})
            dfs.append(df)
        view_df = pd.concat(dfs, axis=1)

        return view_df

    def get_return_chart(self, lookback=None, benchmarks=None):
        """
        Get the return chart of manager portfolios.

        Useful for plotting returns visually.

        Parameters
        ----------
        lookback : date (optional)
            the date the chart should lookback to.
            If none we use the min date.
        benchmarks : list (optional)
            list of tickers to add as benchmarks

        Returns
        -------
        return_chart : plotly chart

        """
        portfolio_repr = ", ".join([portfolio.name for portfolio in self.portfolios])
        logger.info(f"Return chart of following portfolios: [{portfolio_repr}]")

        return_view = self.get_view(view="return")
        cost_view = self.get_view(view="cumulative_cost") * -1
        if lookback is not None:
            lookback = convert_lookback(lookback)
            lookback_date = return_view.index.max() - timedelta(days=lookback)
        else:
            lookback_date = return_view.index.min()

        return_view_filtered = return_view[return_view.index >= lookback_date].copy()
        cost_view_filtered = cost_view[cost_view.index >= lookback_date].copy()
        for col in return_view_filtered.columns:
            # calculates return % over time
            return_view_filtered.loc[return_view_filtered[col] != 0, "change"] = (
                return_view_filtered[col] + cost_view_filtered[col]
            ) / cost_view_filtered[col] - 1
            return_view_filtered = return_view_filtered.drop([col], axis=1)
            return_view_filtered = return_view_filtered.rename(columns={"change": col})
            return_view_filtered[col] = return_view_filtered[col].fillna(0)
            return_view_filtered[col] = (
                return_view_filtered[col] - return_view_filtered[col].iloc[0]
            )

        if benchmarks:
            # get benchmark data and add to return view
            wrapper = Yahoo()
            min_year = return_view_filtered.index.min().year
            price_history = wrapper.stock_history(tickers=benchmarks, min_year=min_year)
            benchmarks = price_history[price_history["date"] >= lookback_date].copy()
            benchmarks["ticker"] = benchmarks["ticker"].apply(
                lambda x: "benchmark_" + x
            )
            benchmarks = benchmarks.pivot(
                index="date", columns="ticker", values="last_price"
            )
            for col in benchmarks.columns:
                # calculates return % over time
                benchmarks[col] = (benchmarks[col] / benchmarks[col].iloc[0]) - 1

            return_view_filtered = pd.concat([return_view_filtered, benchmarks], axis=1)

        return_view_filtered = return_view_filtered.reset_index()

        # create plotly line chart from dataframe
        return_chart = px.line(
            return_view_filtered,
            x="date",
            y=return_view_filtered.columns,
            title="Manager Return Chart",
        )
        return_chart.update_yaxes(tickformat=".1%")

        return return_chart
