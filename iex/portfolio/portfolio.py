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

import argparse
import logging
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

from argparse import RawTextHelpFormatter
from datetime import datetime, timedelta
from pyxirr import xirr

from iex import utils
from iex.portfolio.wrappers import Yahoo

pd.options.display.float_format = "{:,.2f}".format

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


class Portfolio:
    """An Portfolio class used to provide analysis of a portfolio.

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
        config = utils.load_config(config_path, portfolio)

        self.file = str(config["tx_file"])
        self.name = config["name"]
        logger.info(f"creating '{self.name}' portfolio")
        self.filter_type = config["filter_type"]
        self.filter_broker = config["filter_broker"]
        self.funds = config["funds"]
        self.delisted = config["delisted"]
        self.benchmarks = config["benchmarks"]
        self.other_fields = config["other_fields"]
        self.transactions = self.get_transactions(
            filter_type=self.filter_type,
            filter_broker=self.filter_broker,
            other_fields=self.other_fields,
        )
        logger.info(f"read {self.file}")

        self._min_year = self.transactions["date"].min().year
        self.tickers = list(self.transactions["ticker"].unique())
        self.check_tx()
        logger.info(f"You had {len(self.transactions)} transactions")
        self.price_history = self._get_price_history()
        self.transactions_history = self.get_transactions_history(
            tx_df=self.transactions,
            other_fields=self.other_fields,
            benchmarks=self.benchmarks,
        )
        self._max_date = self.transactions_history["date"].max()
        self.return_view = self.get_view(view="return")
        self.cost_view = self.get_view(view="cumulative_cost")

    def refresh(self):
        """Refresh the portfolio."""
        self.__init__(
            tx_file=self.file,
            filter_type=self.filter_type,
            filter_broker=self.filter_broker,
            funds=self.funds,
            delisted=self.delisted,
            benchmarks=self.benchmarks,
            other_fields=self.other_fields,
            name=self.name,
        )

    def get_performance(self, date=None, tx_hist_df=None, lookback=None):
        """Get performance of portfolio and stocks traded at certain point of time.

        Parameters
        ----------
        date : date (default is max date)
            the date the portfolio performance should be as of.
            If none we use the max date.
        tx_hist_df : DataFrame (default is all transactions)
            dataframe to get return percent from
        lookback : int (default is None)
            the number of days to look back

        Returns
        ----------
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

        """
        if date is None:
            date = self._max_date
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        # if lookback provided then apply lookback adjustment
        if lookback is not None:
            tx_hist_df = self._filter_lookback(
                lookback=lookback, adjust_vars=True, tx_hist_df=tx_hist_df
            )
        lookback_date = tx_hist_df["date"].min()
        tx_hist_df["lookback_date"] = lookback_date

        return_pcts = self._get_return_pcts(date=date, tx_hist_df=tx_hist_df)

        performance = tx_hist_df.copy()
        performance = performance[performance["date"] == date]
        performance = performance.reset_index().set_index("ticker")
        performance.drop(["index", "units", "cost"], axis=1, inplace=True)

        condition = performance.index.str.contains("Cash")
        performance.loc["portfolio", "cash"] = performance.loc[
            condition, "market_value"
        ].sum()

        condition = ~performance.index.str.contains(
            "|".join(["Cash", "benchmark", "portfolio"])
        )
        performance.loc["portfolio", "equity"] = performance.loc[
            condition, "market_value"
        ].sum()

        duplicates = performance[performance.index.duplicated()].index
        if len(duplicates) > 0:
            logger.warning(
                f"found {len(duplicates)} duplicate tickers in performance such as {duplicates[0]} on {date}"
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
                "realized",
                "unrealized",
                "cash",
                "equity",
            ]
        ]

        return performance

    def get_transactions(self, filter_type=None, filter_broker=None, other_fields=None):
        """Get the transactions made.

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
        ----------
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
                raise ValueError("Unsupported file format")
        except FileNotFoundError:
            raise ValueError(f"File not found: {self.file}")
        except Exception as e:
            raise ValueError(f"Error loading file: {e}")

        cols = ["date", "ticker", "type", "units", "cost"] + other_fields
        missing_cols = set(cols) - set(transactions.columns)
        if missing_cols:
            raise ValueError(f"Missing columns in file: {missing_cols}")

        transactions = transactions[cols]
        transactions = transactions[~transactions["type"].isin(filter_type)]
        if filter_broker:
            transactions = transactions[transactions["broker"].isin(filter_broker)]

        # handle multiple transactions on same day by grouping
        transactions = (
            transactions.groupby(
                by=["date", "ticker", "type"] + other_fields, dropna=False
            )
            .sum()
            .reset_index()
        )

        # sale price to be based on units bought and not sold (resolves same day sales)
        transactions["date"] = pd.to_datetime(transactions["date"], format="%m/%d/%Y")
        transactions["sale_cost"] = transactions["cost"]
        transactions["sale_units"] = transactions["units"]

        transactions["sale_price"] = (
            transactions["sale_cost"] / transactions["sale_units"]
        ) * -1
        transactions.loc[transactions["ticker"] == "Cash", "sale_price"] = 1

        # sort values descending
        transactions = transactions.sort_values(by="date", ascending=False)

        transactions = transactions[cols + ["sale_price"]]

        return transactions

    def get_transactions_history(
        self, tx_df, price_history=None, other_fields=None, benchmarks=None
    ):
        """Get the history of stock transcations by merging transaction and price history.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        price_history : DataFrame
            Price history DataFrame
        other_fields : list (optional)
            additional fields to include

        Returns
        ----------
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

        transactions_history = self._add_price_history(
            tx_df=transactions, price_history=price_history, other_fields=other_fields
        )
        transactions_history = self._calc_tx_metrics(tx_hist_df=transactions_history)

        transactions_history = self._add_portfolio(tx_hist_df=transactions_history)

        for benchmark in benchmarks:
            benchmark_history = self._add_benchmark(
                tx_df=transactions,
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

    def _get_all_performance(self, step=5, tx_hist_df=None):
        """Get performance of portfolio and stocks traded for duration of portfolio.

        Parameters
        ----------
        step : int (default is 5)
            the interval of dates to pull in perfomance from
        tx_hist_df : DataFrame (default is all transactions)
            dataframe to get return percent from

        Returns
        ----------
        performance : DataFrame
            the performance of individual assets as well as portfolio
                - date
                - average price
                - last price
                - cumulative units
                - cumulative cost
                - market value
                - return
                - return percentage
                - realized
                - unrealized

        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history

        # filter dataframe after first transaction
        min_date = tx_hist_df[tx_hist_df["units"] != 0]["date"].min()
        tx_hist_df = tx_hist_df[tx_hist_df["date"] >= min_date]

        # get dates to loop through func(get_performace)
        dates = pd.to_datetime(tx_hist_df["date"].unique()).sort_values(ascending=False)

        all_performance = pd.DataFrame()
        for date in dates[::step]:
            all_performance = pd.concat(
                [
                    all_performance,
                    self.get_performance(date=date, tx_hist_df=tx_hist_df),
                ]
            )

        all_performance = all_performance.sort_values("date")

        return all_performance

    def _get_price_history(self):
        """Get the history of prices.

        Returns
        ----------
        price_history : DataFrame
            the price history
               - ticker
               - date
               - last price
        """
        tickers = [
            tick for tick in self.tickers if tick not in self.funds + self.delisted
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
                all_funds_df[["date", "ticker", "sale_price"]],
                how="outer",
                on=["date", "ticker"],
            )

            fund_hist_df = fund_hist_df.groupby(["date", "ticker"]).min().reset_index()
            fund_hist_df[["sale_price"]] = fund_hist_df.groupby("ticker")[
                ["sale_price"]
            ].fillna(method="ffill")
            fund_hist_df.rename(columns={"sale_price": "last_price"}, inplace=True)
            price_history = pd.concat([price_history, fund_hist_df])

        # adding cash price history
        if "Cash" in self.tickers:
            logger.info("Adding transaction history for cash transactions")
            df = template_df.copy()
            df["ticker"] = "Cash"
            df["last_price"] = 1
            price_history = pd.concat([price_history, df], axis=0)

        # sort values descending
        price_history = price_history.sort_values(["ticker", "date"], ascending=False)

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
        """Add price history to transactions DataFrame.

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        price_history : DataFrame
            Price history DataFrame
        other_fields : list (optional)
            additional fields to include

        Returns
        ----------
        tx_merge_df : DataFrame
            DataFrame that has transactions and price history
        """
        if other_fields is None:
            other_fields = []

        tickers = list(tx_df["ticker"].unique())

        # create cash transactions from stock purchases
        if "Cash" in tickers:
            cash_tx = tx_df[tx_df["ticker"] != "Cash"].copy()
            cash_tx["ticker"] = "Cash"
            cash_tx["type"] = "Cash"
            cash_tx["units"] = cash_tx["cost"]
            cash_tx["sale_price"] = 1
            tx_df = pd.concat([tx_df, cash_tx], axis=0)
            tx_df.loc[tx_df["ticker"] == "Cash", "cost"] = (
                tx_df.loc[tx_df["ticker"] == "Cash", "cost"] * -1
            )

        # sale price to be based on units bought and not sold (resolves same day sales)
        tx_df["sale_cost"] = tx_df["cost"]
        tx_df["sale_units"] = tx_df["units"]

        tx_df = (
            tx_df.groupby(by=["date", "ticker"] + other_fields)
            .sum(numeric_only=True)
            .reset_index()
        )

        tx_df["sale_price"] = np.where(
            tx_df["units"] == 0,
            0,
            tx_df["sale_cost"] / tx_df["sale_units"] * -1,
        )

        price_history = price_history[price_history["ticker"].isin(tickers)]

        tx_merge_df = (
            pd.merge(
                price_history,
                tx_df[["date", "ticker", "sale_price", "units", "cost"] + other_fields],
                how="outer",
                on=["date", "ticker"],
            )
            .fillna(0)
            .sort_values(by=["ticker", "date"], ignore_index=True)
        )

        # sort values descending
        tx_merge_df = tx_merge_df.sort_values(by="date", ascending=False)

        return tx_merge_df

    def _calc_tx_metrics(self, tx_hist_df):
        """Calculate summation metrics on transactions DataFrame.

        Note:
        does not include metrics for entire 'portfolio' but only for each ticker

        Parameters
        ----------
        tx_hist_df : DataFrame
            Transactions history to calculate metrics on

        Returns
        ----------
        transaction_metrics : DataFrame
            DataFrame containing updated metrics
            - cumulative_units
            - cumulative_cost
            - average_price
            - market_value
            - return
            - unrealized
            - realized
        """
        # sort values ascending to calculat cumsum correctly
        tx_hist_df = tx_hist_df.sort_values(by=["ticker", "date"], ascending=True)

        # cumulative amounts
        tx_hist_df["cumulative_units"] = tx_hist_df.groupby("ticker")[
            "units"
        ].transform(pd.Series.cumsum)
        tx_hist_df["cumulative_cost"] = tx_hist_df.groupby("ticker")["cost"].transform(
            pd.Series.cumsum
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

        tx_hist_df["realized"] = tx_hist_df["return"] - tx_hist_df["unrealized"]

        # fill in zeroes
        for field in [
            "average_price",
            "market_value",
            "return",
            "unrealized",
            "realized",
            "cumulative_units",
        ]:
            condition = tx_hist_df["cumulative_cost"] == 0
            tx_hist_df.loc[condition, field] = tx_hist_df.loc[condition, field].replace(
                0, np.nan
            )

        tx_hist_df["cumulative_cost"] = tx_hist_df["cumulative_cost"].replace(0, np.nan)

        transaction_metrics = tx_hist_df

        return transaction_metrics

    def _add_benchmark(self, tx_df, ticker, price_history=None, other_fields=None):
        """Add a benchmark with transaction history dataframe.

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
        ----------
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
                "There were no transactions in benchmark. Please include cash transactions"
            )

        # add benchmark from cash transactions
        benchmark_tx["ticker"] = ticker
        benchmark_tx["cost"] = -benchmark_tx["cost"]

        # sale price to be based on units bought and not sold (resolves same day sales)
        benchmark_tx["sale_cost"] = benchmark_tx["cost"]
        benchmark_tx["sale_units"] = benchmark_tx["units"]

        benchmark_tx = (
            benchmark_tx.groupby(by=["date", "ticker"] + other_fields)
            .sum(numeric_only=True)
            .reset_index()
        )

        benchmark_tx["sale_price"] = np.where(
            benchmark_tx["units"] == 0,
            0,
            benchmark_tx["sale_cost"] / benchmark_tx["sale_units"] * -1,
        )

        price_history = price_history[price_history["ticker"] == ticker]

        benchmark_tx_hist = (
            pd.merge(
                price_history,
                benchmark_tx[
                    ["date", "ticker", "sale_price", "units", "cost"] + other_fields
                ],
                how="outer",
                on=["date", "ticker"],
            )
            .fillna(0)
            .sort_values(by=["ticker", "date"], ignore_index=True)
        )

        # zero out sale price of offsetting transactions
        condition = benchmark_tx_hist["units"] == 0
        benchmark_tx_hist.loc[condition, "sale_price"] = 0
        # update sale price
        condition = benchmark_tx_hist["units"] != 0
        benchmark_tx_hist.loc[condition, "sale_price"] = benchmark_tx_hist.loc[
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
        """Add the portfolio with transaction history dataframe.

        Parameters
        ----------
        tx__hist_df : DataFrame
            Transactions history

        Returns
        ----------
        portfolio_tx_hist : DataFrame
            DataFrame containing portfolio transaction history
        """
        portfolio_tx_hist = pd.DataFrame()
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        views = [
            "cost",
            "cumulative_cost",
            "market_value",
            "return",
            "unrealized",
            "realized",
        ]
        for view in views:
            cols = ["ticker", "date"] + [view]
            view_df = tx_hist_df[cols]
            view_df = view_df.pivot_table(
                index="date", columns="ticker", values=view, aggfunc="sum"
            )
            view_df["portfolio"] = view_df.loc[
                :, ~view_df.columns.str.contains("benchmark")
            ].sum(axis=1)
            portfolio_tx_hist[view] = view_df["portfolio"]
        portfolio_tx_hist["ticker"] = "portfolio"
        portfolio_tx_hist.reset_index(inplace=True)
        portfolio_tx_hist = pd.concat([tx_hist_df, portfolio_tx_hist], axis=0)

        return portfolio_tx_hist

    def _calc_average_price(self, df):
        """Calculate the average cost basis.

        Parameters
        ----------
        df : DataFrame
            dataframe to apply calculation to

        Returns
        ----------
        df : DataFrame
            dataframe that includes the "average price"
        """
        df.loc[df.index[0], "average_price"] = df.loc[df.index[0], "sale_price"]
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
                        df.loc[df.index[i], "sale_price"] * df.loc[df.index[i], "units"]
                        + df.loc[df.index[i - 1], "cumulative_units"]
                        * df.loc[df.index[i - 1], "average_price"]
                    ) / df.loc[df.index[i], "cumulative_units"]
        return df

    def _calc_average_price_speed(self, df):
        """Calculate the average cost basis.

        Parameters
        ----------
        df : DataFrame
            dataframe to apply calculation to

        Returns
        ----------
        df : DataFrame
            dataframe that includes the "average price"
        """
        df["average_price"] = np.nan
        tx = df[df["units"] != 0]
        if len(tx) != 0:
            tx.loc[tx.index[0], "average_price"] = tx.loc[tx.index[0], "sale_price"]
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
                        tx.loc[tx.index[i], "sale_price"] * tx.loc[tx.index[i], "units"]
                        + tx.loc[tx.index[i - 1], "cumulative_units"]
                        * tx.loc[tx.index[i - 1], "average_price"]
                    ) / tx.loc[tx.index[i], "cumulative_units"]

        # merge average prices back into df
        df.update(tx["average_price"])
        df["average_price"] = df["average_price"].fillna(method="ffill")
        df.loc[df["cumulative_units"] == 0, "average_price"] = 0
        return df

    def _get_return_pct(self, ticker, date, tx_hist_df=None, lookback=None):
        """Get the dollar and time weighted return of a ticker.

        TODO same day transactions do mess up the calculation of returns

        Notes:
        ------
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
              (end_value - start_value - cash_flows) / (start_value + time_weighted_cash_flows)

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
            number of days to lookback
        Returns
        ----------
        return_dict : dict
            dictionary of returns
        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history

        # if lookback provided then filter history to only include that period
        if lookback is not None:
            tx_hist_df = self._filter_lookback(
                lookback=lookback, adjust_vars=False, tx_hist_df=tx_hist_df
            )

        transactions = tx_hist_df[tx_hist_df["cost"] != 0]

        # get the current price, entry price, and transactions
        current_price = tx_hist_df[
            (tx_hist_df["ticker"] == ticker) & (tx_hist_df["date"] == date)
        ]
        entry_price = tx_hist_df[
            (tx_hist_df["ticker"] == ticker)
            & (tx_hist_df["date"] == tx_hist_df["date"].min())
        ].copy()
        ticker_transactions = transactions[
            (transactions["ticker"] == ticker) & (transactions["date"] <= date)
        ].copy()

        # combine the entry price, transactions, and current price

        # entry price is the first transaction. To offset transactional costs on the same day
        # the entry price removes the cost. Also xirr does not work with a start of 0 or nan
        # so removing those transactions as well.
        entry_price["market_value"] = entry_price["market_value"] + entry_price["cost"]
        entry_price = entry_price[["date", "ticker", "units", "market_value"]]
        entry_price.loc[:, "market_value"] *= -1
        entry_price = entry_price[
            (entry_price["market_value"] != 0) & (~entry_price["market_value"].isna())
        ]
        entry_price = entry_price.reset_index(drop=True)
        ticker_transactions["market_value"] = ticker_transactions["cost"]
        current_price = current_price[["date", "ticker", "units", "market_value"]]

        ticker_transactions = pd.concat(
            [entry_price, ticker_transactions, current_price], ignore_index=True
        ).sort_values(by="date", ascending=False)
        ticker_transactions["market_value"] = ticker_transactions[
            "market_value"
        ].replace(np.nan, 0)

        # makes sure that ticker had transactions both negative
        # and positive to calculate return
        dwrr_return_pct = np.NaN
        dwrr_ann_return_pct = np.NaN
        mdrr_return_pct = np.NaN
        mdrr_ann_return_pct = np.NaN
        if ticker_transactions.empty:
            logger.debug(
                f"There were no transactions for {ticker} to calculate the return"
            )

        elif (
            len(ticker_transactions) == 1
            and ticker_transactions["market_value"].iloc[0] == 0
        ):
            logger.debug(
                f"The ticker {ticker} is in portfolio but has no transactions"
                " to calculate the return"
            )

        elif (
            not min(ticker_transactions["market_value"])
            < 0
            < max(ticker_transactions["market_value"])
        ):
            logger.warning(
                f"The transactions for {ticker} did not have positive and negatives"
            )

        else:
            # for annualizing returns need the days
            start_date = ticker_transactions["date"].iloc[-1]
            end_date = ticker_transactions["date"].iloc[0]
            days = (end_date - start_date).days

            # calculating the dwrr return
            dwrr_ann_return_pct = xirr(
                ticker_transactions["date"], ticker_transactions["market_value"]
            )
            # where dwrr can't be calculated
            if dwrr_ann_return_pct is None:
                pass
            elif dwrr_ann_return_pct > 1000:
                dwrr_return_pct = (1 + dwrr_ann_return_pct) ** (days / 365) - 1
                dwrr_ann_return_pct = np.NaN
            else:
                dwrr_return_pct = (1 + dwrr_ann_return_pct) ** (days / 365) - 1

            # calculating the dietz return
            ticker_transactions["weight"] = (
                days - (ticker_transactions["date"] - start_date).dt.days
            ) / (days)
            ticker_transactions["weighted_value"] = (
                ticker_transactions["market_value"] * ticker_transactions["weight"]
            )
            mdrr_return_pct = ticker_transactions["market_value"].sum() / (
                ticker_transactions["weighted_value"].sum() * -1
            )
            # where mdrr can't be calculated
            if mdrr_return_pct is None:
                pass
            elif mdrr_return_pct > 1000:
                pass
            elif mdrr_return_pct < -1:
                pass
            else:
                mdrr_ann_return_pct = (1 + mdrr_return_pct) ** (365 / days) - 1

        return_dict = {}
        return_dict["dwrr_return_pct"] = dwrr_return_pct
        return_dict["dwrr_ann_return_pct"] = dwrr_ann_return_pct
        return_dict["mdrr_return_pct"] = mdrr_return_pct
        return_dict["mdrr_ann_return_pct"] = mdrr_ann_return_pct

        return return_dict

    def _get_return_pcts(self, date=None, tx_hist_df=None, lookback=None):
        """Get the dollar weighted return of transactions.

        Parameters
        ----------
        date : date (optional)
            date on which to perform the returns as of
        tx_hist_df : DataFrame (optional)
            dataframe to get return percent from
        lookback : int (optional)
            number of days to lookback

        Returns
        ----------
        return_pcts : DataFrame
            returns of all transactions
        """
        if date is None:
            date = self._max_date
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history

        tickers = list(tx_hist_df["ticker"].unique())

        return_pcts = pd.DataFrame()

        # get return of each ticker
        for ticker in tickers:
            return_dict = self._get_return_pct(
                ticker=ticker,
                date=date,
                tx_hist_df=tx_hist_df,
                lookback=lookback,
            )

            return_pcts = pd.concat(
                [
                    return_pcts,
                    pd.DataFrame(
                        {
                            "ticker": [ticker],
                            "dwrr_pct": return_dict["dwrr_return_pct"],
                            "dwrr_ann_pct": return_dict["dwrr_ann_return_pct"],
                        }
                    ),
                ]
            )

        return_pcts = return_pcts.set_index(["ticker"])

        return return_pcts

    def get_view(self, view="market_value", tx_hist_df=None):
        """Get the a specific view of the portfolio.

        Useful for plotting returns visually.

        Parameters
        ----------
        view : str
            column to sum over on the portfolio dataframe
               - e.g. "market_value", "return", "cumulative_cost", "realized"
        tx_hist_df : DataFrame
            dataframe to get return percent from

        Returns
        ----------
        view_df : DataFrame
        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        cols = ["ticker", "date"] + [view]
        view_df = tx_hist_df[cols]
        view_df = view_df.pivot_table(
            index="date", columns="ticker", values=view, aggfunc="sum"
        )
        view_df["portfolio"] = view_df.loc[
            :, ~view_df.columns.str.contains("benchmark")
        ].sum(axis=1)

        return view_df

    def _filter_lookback(self, lookback, adjust_vars=False, tx_hist_df=None):
        """Modify the transactions history dataframe to only include lookback.

        Parameters
        ----------
        lookback : int
            number of days to lookback
        adjust_vars : bool
            whether to adjust the variables return, realized, and unrealized
        tx_hist_df : DataFrame (optional)
            stock dataframe to get return percent from

        Returns
        ----------
        lookback_df : DataFrame
            dataframe that includes the lookback period
        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
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
            variables = ["return", "unrealized", "realized"]

            # Grouping the DataFrame by 'ticker' and applying the operation to each group
            for variable in variables:
                lookback_df[variable] = lookback_df.groupby("ticker")[
                    variable
                ].transform(lambda x: x - x.iloc[-1])

        return lookback_df

    def check_tx(self, tx_df=None):
        """Check that transactions have correct data.

        Parameters
        ----------
        tx_df : DataFrame
            dataframe to performe checks on

        Returns
        ----------
        portfolio_checks_failed : int
        """
        if tx_df is None:
            tx_df = self.transactions

        portfolio_checks_failed = 0
        # buy checks
        if any(tx_df[tx_df["type"] == "SELL"]["units"] > 0):
            err_df = tx_df[(tx_df["type"] == "SELL") & (tx_df["units"] > 0)]
            logger.warning(
                f"There were transactions that had positive units for SELL "
                f"type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['units']} units"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "SELL"]["cost"] < 0):
            err_df = tx_df[(tx_df["type"] == "SELL") & (tx_df["cost"] < 0)]
            logger.warning(
                f"There were transactions that had negative cost for SELL "
                f"type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # sell short checks
        if any(tx_df[tx_df["type"] == "SELL SHORT"]["units"] > 0):
            err_df = tx_df[(tx_df["type"] == "SELL SHORT") & (tx_df["units"] > 0)]
            logger.warning(
                f"There were transactions that had positive units for SELL "
                f"SHORT type such as {err_df.iloc[1]['ticker']} "
                f"with {err_df.iloc[1]['units']} units"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "SELL SHORT"]["cost"] < 0):
            err_df = tx_df[(tx_df["type"] == "SELL SHORT") & (tx_df["cost"] < 0)]
            logger.warning(
                f"There were transactions that had negative cost for SELL SHORT "
                f"type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # buy
        if any(tx_df[tx_df["type"] == "BUY"]["units"] < 0):
            err_df = tx_df[(tx_df["type"] == "BUY") & (tx_df["units"] < 0)]
            logger.warning(
                f"There were transactions that had negative units for BUY type "
                f"such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['units']} units "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "BUY"]["cost"] > 0):
            err_df = tx_df[(tx_df["type"] == "BUY") & (tx_df["cost"] > 0)]
            logger.warning(
                f"There were transactions that had positive cost for BUY type "
                f"such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # buy cover
        if any(tx_df[tx_df["type"] == "BUY COVER"]["units"] < 0):
            err_df = tx_df[(tx_df["type"] == "BUY COVER") & (tx_df["units"] < 0)]
            logger.warning(
                f"There were transactions that had negative units for BUY "
                f"COVER type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['units']} units "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "BUY COVER"]["cost"] > 0):
            err_df = tx_df[(tx_df["type"] == "BUY COVER") & (tx_df["cost"] > 0)]
            logger.warning(
                f"There were transactions that had positive cost for BUY COVER type "
                f"such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # type checks
        tx_allowed_types = ["BOOK", "BUY", "Cash", "SELL", "BUY COVER", "SELL SHORT"]
        tx_types = tx_df["type"].unique()
        for tx_type in tx_types:
            if tx_type not in tx_allowed_types:
                logger.warning(f"This type '{tx_type}' is not in {tx_allowed_types}")
                portfolio_checks_failed = portfolio_checks_failed + 1

        # column checks
        tx_needed_columns = ["ticker", "date", "type", "units", "cost"]
        tx_columns = list(tx_df.columns)
        for tx_needed_column in tx_needed_columns:
            if tx_needed_column not in tx_columns:
                logger.warning(
                    f"This column '{tx_needed_column}' is needed, and not "
                    f"in {tx_columns}"
                )
                portfolio_checks_failed = portfolio_checks_failed + 1

        # date checks
        tx_df_min = tx_df["date"].min()
        tx_df_max = tx_df["date"].max()
        stock_dates = (
            mcal.get_calendar("NYSE")
            .schedule(start_date=tx_df_min, end_date=tx_df_max)
            .index
        )
        invalid_dt = tx_df["date"][~tx_df["date"].isin(stock_dates)].to_list()
        invalid_dt = [datetime.strftime(i, "%Y-%m-%d") for i in invalid_dt]
        if len(invalid_dt) > 0:
            logger.warning(
                f"{len(invalid_dt)} transaction(s) dates were done outside of stock market "
                f"dates such as {invalid_dt} \n"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        return portfolio_checks_failed


class Manager:
    """Manager is a class that analyzes multiple portfolios.

    Parameters
    ----------
    portfolios : list
        list of portfolios in the Portfolio class to analyze.
    """

    def __init__(
        self,
        portfolios,
    ):
        self.portfolios = portfolios

    def refresh(self):
        """Refresh the portfolio."""
        # refresh the portfolio data
        for portfolio in self.portfolios:
            portfolio.refresh()
        self.__init__(
            portfolios=self.portfolios,
        )
        logger.info("Refreshed portfolios.")

    def get_summary(self, date=None, lookback=None):
        """Get summary of portfolios.

        Parameters
        ----------
        date : date
            the date the asset summary should be as of.
            If none we use the max date.
        lookback : int (default is None)
            the number of days to look back

        Returns
        ----------
        summary : DataFrame
            the summary of portfolios
                - cash
                - equity
                - market value
                - return
                - benchmark return

        """
        portfolio_repr = ", ".join([portfolio.name for portfolio in self.portfolios])
        logger.info(f"Summarizing following portfolios: [{portfolio_repr}]")
        dfs = []
        for portfolio in self.portfolios:
            performance = portfolio.get_performance(date=date, lookback=lookback)
            df = performance[performance.index == "portfolio"].rename(
                index={"portfolio": portfolio.name}
            )
            # adding benchmark to the summary
            benchmark = performance[performance.index.str.contains("benchmark")].head(1)
            benchmark_dict = {}
            if not benchmark.empty:
                benchmark_dict["benchmark"] = benchmark.index.values[0].split("-")[1]
                benchmark_dict["benchmark_dwrr_pct"] = benchmark["dwrr_pct"].values[0]

            df = df.assign(**benchmark_dict)
            dfs.append(df)
        summary = pd.concat(dfs)

        return summary

    def get_view(self, view="market_value"):
        """Get the view of portfolios.

        Useful for plotting returns visually.

        Parameters
        ----------
        view : str
            column to sum over on the portfolio dataframe
               - e.g. "market_value", "return", "cumulative_cost", "realized"

        Returns
        ----------
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


#
# https://patorjk.com/software/taag/ using BIG
#    _____ _      _____
#   / ____| |    |_   _|
#  | |    | |      | |
#  | |    | |      | |
#  | |____| |____ _| |_
#   \_____|______|_____|
#


def _create_argparser():
    description = """Provides a portfolio tracker."""
    _parser = argparse.ArgumentParser(
        description=description,
        formatter_class=RawTextHelpFormatter,
    )

    # add the command-line arguments
    _parser.add_argument(
        "command",
        choices=["portfolio", "manager"],
        help="The command to run (portfolio or manager)",
    )
    _parser.add_argument(
        "--date",
        type=str,
        help="The date to use for performance calculations (YYYY-MM-DD)",
    )
    _parser.add_argument(
        "--lookback",
        type=int,
        default=30,
        help="The number of days to look back for performance calculations",
    )

    return _parser


parser = _create_argparser()


def cli():
    """Portfolio command line interface."""
    args = parser.parse_args()

    if args.command == "portfolio":
        # create a Portfolio object
        portfolio = Portfolio()

        # get the performance data
        performance = portfolio.get_performance(date=args.date, lookback=args.lookback)

        # print the performance data
        print(performance)

    elif args.command == "manager":
        # create a Manager object
        manager = Manager()

        # get the summary data
        summary = manager.get_summary(date=args.date, lookback=args.lookback)

        # print the summary data
        print(summary)


if __name__ == "__main__":
    cli()
