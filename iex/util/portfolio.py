"""
Creates a portfolio tracker.

This initiates a class with a number of objects, such as:
   - file : the transaction file locations
   - funds : symbols that are considered funds
   - transactions : the transactions the occured
   - transaction_history : provides the symbol price history
as well as a few functions
   - perfomance : this function will provide the performance of portfolio
"""

import numpy as np
import pandas as pd
import yfinance as yf

from datetime import datetime
from pyxirr import xirr

pd.options.display.float_format = "{:,.2f}".format


class Portfolio:
    """An object containing information about portfolio.

    Parameters
    ----------
    tx_file : str
        the location of the transaction file
    filter_type : list (optional)
        the transaction types to exclude from analysis
        e.g. dividends, cash
    filter_broker : list (optional)
        the brokers to include in analysis
        e.g. company_a, company_b
    funds : list (optional)
        the symbols that should be analyzed as funds. These symbols won't have any
        yahoo finance reference, so we use transaction prices to fill in blank values
    delisted : list (optional)
        similar to funds. These symbols won't have any yahoo finance reference, so we
        use transaction prices to fill in blank values
    benchmark : list (optional)
        the symbols to use as a benchmark to compare against.
    other_fields : list (optional)
        additional fields to include
    """

    def __init__(
        self,
        tx_file,
        filter_type=None,
        filter_broker=None,
        funds=None,
        delisted=None,
        benchmark=None,
        other_fields=None,
    ):

        if filter_type is None:
            filter_type = []
        if filter_broker is None:
            filter_broker = []
        if funds is None:
            funds = []
        if delisted is None:
            delisted = []
        if benchmark is None:
            benchmark = []
        if other_fields is None:
            other_fields = []

        print("read '{}'".format(tx_file))
        self.file = tx_file
        self.funds = funds
        self.delisted = delisted
        self.benchmark = benchmark
        self.transactions = self._get_transactions(
            filter_type=filter_type,
            filter_broker=filter_broker,
            other_fields=other_fields,
        )
        self._min_year = self.transactions["date"].min().year
        self.tickers = list(self.transactions["ticker"].unique())
        print(f"You had {len(self.transactions)} transactions")
        self.check_tx()
        self.price_history = self._get_price_history()
        self.transactions_history = self._get_transactions_history(
            other_fields=other_fields, benchmark=benchmark
        )
        self._max_date = self.transactions_history["date"].max()
        self.return_view = self._get_view(view="return")
        self.cost_view = self._get_view(view="cumulative_cost")

    def get_performance(self, date=None, tx_hist_df=None):
        """Get performance of portfolio and stocks traded at certain point of time.

        Parameters
        ----------
        date : date (default is max date)
            the date the portfolio performance should be as of.
            If none we use the max date.
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
        if date is None:
            date = self._max_date
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history

        return_pcts = self._get_return_pcts(date, tx_hist_df)
        performance = tx_hist_df.copy()
        performance = performance[performance["date"] == date]
        performance = performance.reset_index().set_index("ticker")
        performance.drop(["index", "units", "cost"], axis=1, inplace=True)

        performance.loc["portfolio"] = np.nan
        performance.loc["portfolio", "date"] = pd.to_datetime(
            date, infer_datetime_format=True
        )
        # remove benchmark from portfolio calculation
        if "broker" in performance.columns:
            condition = performance["broker"] != "benchmark"
        else:
            condition = performance["date"] != ""
        performance.loc["portfolio", "cumulative_cost"] = performance.loc[
            condition, "cumulative_cost"
        ].sum()
        performance.loc["portfolio", "market_value"] = performance.loc[
            condition, "market_value"
        ].sum()
        performance.loc["portfolio", "return"] = performance.loc[
            condition, "return"
        ].sum()
        performance.loc["portfolio", "realized"] = performance.loc[
            condition, "realized"
        ].sum()
        performance.loc["portfolio", "unrealized"] = performance.loc[
            condition, "unrealized"
        ].sum()

        duplicates = performance[performance.index.duplicated()].index
        if len(duplicates) > 0:
            print(
                f" found {len(duplicates)} duplicate tickers in performance such as {duplicates[0]} on {date}"
            )

        performance = pd.concat([performance, return_pcts], axis=1, join="inner")

        performance = performance[
            [
                "date",
                "average_price",
                "last_price",
                "cumulative_units",
                "cumulative_cost",
                "market_value",
                "return",
                "return_pct",
                "realized",
                "unrealized",
            ]
        ]

        return performance

    def get_all_performance(self, step=5, tx_hist_df=None):
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

    def _get_transactions(
        self, only_tickers=None, filter_type=None, filter_broker=None, other_fields=None
    ):
        """Get the transactions made.

        Parameters
        ----------
        tickers : list (optional)
            list of tickers to only include
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
        if only_tickers is None:
            only_tickers = []
        if filter_type is None:
            filter_type = []
        if filter_broker is None:
            filter_broker = []
        if other_fields is None:
            other_fields = []

        cols = ["date", "ticker", "type", "units", "cost"] + other_fields
        transactions = pd.read_excel(self.file, engine="openpyxl")
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

        transactions["date"] = pd.to_datetime(transactions["date"], format="%d/%m/%Y")

        transactions["sale_price"] = (transactions["cost"] / transactions["units"]) * -1
        transactions.loc[transactions["ticker"] == "Cash", "sale_price"] = 1

        if only_tickers:
            transactions = transactions[transactions["ticker"].isin(only_tickers)]

        transactions = transactions.sort_values(by="date", ascending=False)

        return transactions

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
        ] + self.benchmark

        if self.benchmark:
            print(f"Adding {self.benchmark} as a benchmark")
        price_history = yf.download(tickers, start=datetime(self._min_year, 1, 1))
        self._clean_index(clean_df=price_history, lvl=0)
        price_history.index.rename("date", inplace=True)
        price_history.columns.rename("measure", level=0, inplace=True)
        price_history.columns.rename("ticker", level=1, inplace=True)

        price_history = price_history.stack(level="ticker")
        price_history.index = price_history.index.swaplevel("date", "ticker")
        price_history.sort_index(axis=0, level="ticker", inplace=True)
        price_history = price_history.reset_index()
        cols = ["ticker", "date", "adj_close"]
        price_history = price_history[cols]
        price_history.rename(columns={"adj_close": "last_price"}, inplace=True)

        # adding fund price history
        transactions = self.transactions
        template_df = pd.DataFrame(price_history["date"].unique(), columns=["date"])
        if self.funds:
            print(
                f"Did not get price info for {self.funds} and will use transaction"
                " price to develop price history, since they are funds and not"
                " available in stock exchanges"
            )
        if self.delisted:
            print(
                f"Did not get price info for {self.delisted} and will use transaction"
                " price to develop price history, since they are delisted and not"
                " available in stock exchanges"
            )
        for fund in self.funds + self.delisted:
            df = template_df.copy()
            fund_df = transactions[transactions["ticker"] == fund]
            df = pd.merge(
                df,
                fund_df[["date", "sale_price"]],
                how="outer",
                on=["date"],
            )
            df["ticker"] = fund
            df = df.groupby("date").min().reset_index()
            df[["sale_price"]] = df[["sale_price"]].fillna(method="ffill")
            df.rename(columns={"sale_price": "last_price"}, inplace=True)
            price_history = pd.concat([price_history, df])

        # adding cash price history
        if "Cash" in self.tickers:
            print("Adding transaction history for cash transactions")
            df = template_df.copy()
            df["ticker"] = "Cash"
            df["last_price"] = 1
            price_history = pd.concat([price_history, df])

        price_history = price_history.sort_values(["ticker", "date"])

        return price_history

    def calc_transaction_metrics(
        self, tx_df, price_history=None, other_fields=None, benchmark=None
    ):
        """Calculate summation metrics on transactions DataFrame.

        Note:
        does not include portfolio metrics

        Parameters
        ----------
        tx_df : DataFrame
            Transactions to calculate metrics on
        price_history : DataFrame
            Price history DataFrame
        other_fields : list (optional)
            additional fields to include
        benchmark : list (optional)
            the symbols to use as a benchmark to compare against.

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
        if other_fields is None:
            other_fields = []
        if benchmark is None:
            benchmark = []

        if benchmark != [] and "broker" not in other_fields:
            raise Exception(
                "When providing a benchmark, the 'broker' column in `other_fields` must be passed as well"
            )

        tx_df = tx_df.copy()
        transactions = tx_df[(tx_df["cost"] != 0) | (tx_df["units"] != 0)]
        tickers = list(transactions["ticker"].unique()) + benchmark

        # create cash transactions from stock purchases
        if "Cash" in tickers:
            cash_tx = transactions[transactions["ticker"] != "Cash"].copy()
            cash_tx["ticker"] = "Cash"
            cash_tx["type"] = "Cash"
            cash_tx["units"] = cash_tx["cost"]
            cash_tx["sale_price"] = 1
            # add benchmark from cash transactions
            if benchmark:
                benchmark_tx = transactions[transactions["ticker"] == "Cash"].copy()
                benchmark_tx["ticker"] = benchmark[0]
                benchmark_tx["broker"] = "benchmark"
                benchmark_tx["cost"] = -benchmark_tx["cost"]
                transactions = pd.concat([transactions, benchmark_tx])
            transactions = pd.concat([transactions, cash_tx])
            transactions.loc[transactions["ticker"] == "Cash", "cost"] = (
                transactions.loc[transactions["ticker"] == "Cash", "cost"] * -1
            )

        transactions = (
            transactions.groupby(by=["date", "ticker"] + other_fields)
            .sum(numeric_only=True)
            .reset_index()
        )
        # aggregating sale_price for a single day
        transactions["sale_price"] = np.where(
            transactions["units"] == 0,
            0,
            transactions["cost"] / transactions["units"] * -1,
        )
        if price_history is None:
            price_history = self.price_history

        price_history = price_history[price_history["ticker"].isin(tickers)]

        tx_hist_df = (
            pd.merge(
                price_history,
                transactions[
                    ["date", "ticker", "sale_price", "units", "cost"] + other_fields
                ],
                how="outer",
                on=["date", "ticker"],
            )
            .fillna(0)
            .sort_values(by=["ticker", "date"], ignore_index=True)
        )

        # update benchmark values
        if benchmark:
            # zero out sale price of offsetting transactions
            condition = (tx_hist_df["broker"] == "benchmark") & (
                tx_hist_df["units"] == 0
            )
            tx_hist_df.loc[condition, "sale_price"] = 0
            # update sale price and units of benchmark
            condition = (tx_hist_df["broker"] == "benchmark") & (
                tx_hist_df["sale_price"] > 0
            )
            tx_hist_df.loc[condition, "sale_price"] = tx_hist_df.loc[
                condition, "last_price"
            ]
            tx_hist_df.loc[condition, "units"] = -(
                tx_hist_df.loc[condition, "cost"]
                / tx_hist_df.loc[condition, "last_price"]
            )

        # cumulative amounts
        tx_hist_df["cumulative_units"] = tx_hist_df.groupby("ticker")[
            "units"
        ].transform(pd.Series.cumsum)
        tx_hist_df["cumulative_cost"] = tx_hist_df.groupby("ticker")["cost"].transform(
            pd.Series.cumsum
        )

        # average price
        tx_hist_df = tx_hist_df.groupby("ticker", group_keys=False).apply(
            self._calc_average_price
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

        # fill in other_fields null values
        for field in other_fields:
            tx_hist_df[field] = tx_hist_df[field].replace(0, np.nan)
            tx_hist_df[field] = tx_hist_df.groupby(["ticker"], group_keys=False)[
                field
            ].apply(lambda x: x.ffill().bfill())

        # sort values
        tx_hist_df = tx_hist_df.sort_values(by=["ticker", "date"], ignore_index=True)

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

        transaction_metrics = transaction_metrics.sort_values(
            by="date", ascending=False
        )

        return transaction_metrics

    def _get_transactions_history(
        self, only_tickers=None, other_fields=None, benchmark=None
    ):
        """Get the history of stock transcations by merging transaction and price history.

        Parameters
        ----------
        only_tickers : list (optional)
            list of tickers to only include
        other_fields : list (optional)
            additional fields to include

        Returns
        ----------
        transactions_history : DataFrame
            the price history of stock transactions
        """
        if only_tickers is None:
            only_tickers = []
        if other_fields is None:
            other_fields = []
        if benchmark is None:
            benchmark = []

        transactions = self.transactions

        transactions_history = self.calc_transaction_metrics(
            transactions, other_fields=other_fields, benchmark=benchmark
        )

        # filter tickers
        if only_tickers:
            transactions_history = transactions_history[
                transactions_history["ticker"].isin(only_tickers)
            ]

        return transactions_history

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

    def _get_return_pct(self, ticker, date, tx_hist_df=None):
        """Get the dollar weighted return of a ticker.

        Parameters
        ----------
        ticker : str
            ticker that will be used to calculate metric
        date : date
            date on which to perform the returns as of
        tx_hist_df : DataFrame
            stock dataframe to get return percent from
        Returns
        ----------
        return_pct : float
            the dollar weighted return of ticker
        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        transactions = tx_hist_df[tx_hist_df["cost"] != 0]

        # get the current price and transactions
        if ticker == "portfolio":
            current_price = tx_hist_df[tx_hist_df["date"] == date]
            ticker_transactions = transactions[transactions["date"] <= date].copy()

        else:
            current_price = tx_hist_df[
                (tx_hist_df["ticker"] == ticker) & (tx_hist_df["date"] == date)
            ]
            ticker_transactions = transactions[
                (transactions["ticker"] == ticker) & (transactions["date"] <= date)
            ].copy()

        # combine the current price and transactions
        current_price = current_price[["date", "ticker", "units", "market_value"]]
        ticker_transactions["market_value"] = ticker_transactions["cost"]
        ticker_transactions = pd.concat(
            [ticker_transactions, current_price], ignore_index=True
        )
        ticker_transactions["market_value"] = ticker_transactions[
            "market_value"
        ].replace(np.nan, 0)

        # makes sure that ticker had transactions both negative
        # and positive to calculate IRR
        if ticker_transactions.empty:
            return_pct = np.NaN

        elif (
            not min(ticker_transactions["market_value"])
            < 0
            < max(ticker_transactions["market_value"])
        ):
            return_pct = np.NaN

        else:

            return_pct = xirr(
                ticker_transactions["date"], ticker_transactions["market_value"]
            )

            # where IRR can't be calculated
            if return_pct is None:
                return_pct = np.NaN
            elif return_pct > 1000:
                return_pct = np.NaN

        return return_pct

    def _get_return_pcts(self, date=None, tx_hist_df=None):
        """Get the dollar weighted return of transactions.

        Parameters
        ----------
        date : date (optional)
            date on which to perform the returns as of
        tx_hist_df : DataFrame
            dataframe to get return percent from

        Returns
        ----------
        return_pcts : DataFrame
            dollar weighted returns of all transactions
        """
        if date is None:
            date = self._max_date
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history

        tickers = list(tx_hist_df["ticker"].unique())

        return_pcts = pd.DataFrame()

        # get return of each ticker
        for ticker in tickers:
            ticker_return = self._get_return_pct(
                ticker=ticker,
                date=date,
                tx_hist_df=tx_hist_df,
            )

            return_pcts = pd.concat(
                [
                    return_pcts,
                    pd.DataFrame({"ticker": [ticker], "return_pct": ticker_return}),
                ]
            )

        # get portfolio return
        if "broker" in tx_hist_df.columns:
            condition = tx_hist_df["broker"] != "benchmark"
        else:
            condition = tx_hist_df["date"] != ""
        portfolio_return = self._get_return_pct(
            ticker="portfolio",
            date=date,
            tx_hist_df=tx_hist_df[condition],
        )
        return_pcts = pd.concat(
            [
                return_pcts,
                pd.DataFrame({"ticker": ["portfolio"], "return_pct": portfolio_return}),
            ]
        ).set_index(["ticker"])

        return return_pcts

    def _clean_index(self, clean_df, lvl):
        """Clean the index of DataFrame.

        Parameters
        ----------
        clean_df : DataFrame
            the dataframe on which to clean
        lvl : int
            the level of index to clean

        Returns
        ----------
        clean_df : DataFrame
            a clean DataFrame
        """
        idx = clean_df.columns.levels[lvl]
        idx = (
            idx.str.lower()
            .str.replace(".", "", regex=False)
            .str.replace("(", "", regex=False)
            .str.replace(")", "", regex=False)
            .str.replace(" ", "_", regex=False)
            .str.replace("_/_", "/", regex=False)
        )
        clean_df.columns = clean_df.columns.set_levels(idx, level=lvl)

        return clean_df

    def _get_view(self, view="market_value", tx_hist_df=None):
        """Get the a specific view of the portfolio.

        Useful for plotting returns visually.

        Parameters
        ----------
        view : str
            column to sum over on the portfolio dataframe
               - e.g. "market_value", "return", "cumulative_cost"
        tx_hist_df : DataFrame
            dataframe to get return percent from

        Returns
        ----------
        view_df : DataFrame
        """
        if tx_hist_df is None:
            tx_hist_df = self.transactions_history
        portfolio_col = ["ticker", "date"] + [view]
        view_df = tx_hist_df[portfolio_col]
        view_df = view_df.pivot_table(
            index="date", columns="ticker", values=view, aggfunc="sum"
        )
        view_df["portfolio"] = view_df.sum(axis=1)

        return view_df

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
            print(
                f"There were transactions that had positive units for SELL "
                f"type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['units']} units"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "SELL"]["cost"] < 0):
            err_df = tx_df[(tx_df["type"] == "SELL") & (tx_df["cost"] < 0)]
            print(
                f"There were transactions that had negative cost for SELL "
                f"type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # sell short checks
        if any(tx_df[tx_df["type"] == "SELL SHORT"]["units"] > 0):
            err_df = tx_df[(tx_df["type"] == "SELL SHORT") & (tx_df["units"] > 0)]
            print(
                f"There were transactions that had positive units for SELL "
                f"SHORT type such as {err_df.iloc[1]['ticker']} "
                f"with {err_df.iloc[1]['units']} units"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "SELL SHORT"]["cost"] < 0):
            err_df = tx_df[(tx_df["type"] == "SELL SHORT") & (tx_df["cost"] < 0)]
            print(
                f"There were transactions that had negative cost for SELL SHORT "
                f"type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost"
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # buy
        if any(tx_df[tx_df["type"] == "BUY"]["units"] < 0):
            err_df = tx_df[(tx_df["type"] == "BUY") & (tx_df["units"] < 0)]
            print(
                f"There were transactions that had negative units for BUY type "
                f"such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['units']} units "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "BUY"]["cost"] > 0):
            err_df = tx_df[(tx_df["type"] == "BUY") & (tx_df["cost"] > 0)]
            print(
                f"There were transactions that had positive cost for BUY type "
                f"such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['cost']} cost "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        # buy cover
        if any(tx_df[tx_df["type"] == "BUY COVER"]["units"] < 0):
            err_df = tx_df[(tx_df["type"] == "BUY COVER") & (tx_df["units"] < 0)]
            print(
                f"There were transactions that had negative units for BUY "
                f"COVER type such as {err_df.iloc[1]['ticker']} with "
                f"{err_df.iloc[1]['units']} units "
            )
            portfolio_checks_failed = portfolio_checks_failed + 1

        if any(tx_df[tx_df["type"] == "BUY COVER"]["cost"] > 0):
            err_df = tx_df[(tx_df["type"] == "BUY COVER") & (tx_df["cost"] > 0)]
            print(
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
                print(f"This type '{tx_type}' is not in {tx_allowed_types}")
                portfolio_checks_failed = portfolio_checks_failed + 1

        # column checks
        tx_needed_columns = ["ticker", "date", "type", "units", "cost"]
        tx_columns = list(tx_df.columns)
        for tx_needed_column in tx_needed_columns:
            if tx_needed_column not in tx_columns:
                print(
                    f"This column '{tx_needed_column}' is needed, and not "
                    f"in {tx_columns}"
                )
                portfolio_checks_failed = portfolio_checks_failed + 1

        return portfolio_checks_failed
