"""
Creates a portfolio tracker.

This initiates a class with a number of objects, such as:
   - file : the transaction file locations
   - blacklist : the symbols to avoid
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


class portfolio:
    """An object containing information about portfolio.

    Parameters
    ----------
    tx_file : str
        the location of the transaction file
    filter_type : list (optional)
        the transaction types to exclude from analysis
        e.g. dividends, cash
    blacklist : list (optional)
        the stock symbols to exclude from analysis
    funds : list (optional)
        the symbols that should be analyzed as funds. These symbols won't have any
        yahoo finance reference, so we use transaction prices to fill in blank values
    other_fields : list (optional)
        additional fields to include
    """

    def __init__(
        self,
        tx_file,
        filter_type=None,
        blacklist=["VSLR", "HTZ"],
        funds=None,
        other_fields=None,
    ):

        if filter_type is None:
            filter_type = []
        if funds is None:
            funds = []
        if other_fields is None:
            other_fields = []

        print("read '{}'".format(tx_file))
        self.file = tx_file
        self.blacklist = blacklist
        self.funds = funds
        self.transactions = self._get_transactions(
            filter_type=filter_type, other_fields=other_fields
        )
        self._min_year = self.transactions["date"].min().year
        self.tickers = list(self.transactions["ticker"].unique())
        print("You had {} transactions".format(len(self.transactions)))
        self.price_history = self._get_price_history()
        self.transactions_history = self._get_transactions_history(
            other_fields=other_fields
        )
        self._max_date = self.transactions_history["date"].max()
        self.portfolio_view = self._get_portfolio_view()
        self.cost_view = self._get_cost_view()

    def get_performance(self, date=None, tx_df=None):
        """Get performance of portfolio and stocks traded at certain point of time.

        Parameters
        ----------
        date : date (default is max date)
            the date the portfolio performance should be as of.
            If none we use the max date.
        tx_df : DataFrame (default is all transactions)
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
        if tx_df is None:
            tx_df = self.transactions_history

        return_pcts = self._get_return_pcts(date, tx_df)
        performance = tx_df.copy()
        performance = performance[performance["date"] == date]
        performance = performance.reset_index().set_index("ticker")
        performance.drop(["index", "units", "cost"], axis=1, inplace=True)

        performance.loc["portfolio"] = 0
        performance.loc["portfolio", "cumulative_cost"] = performance[
            performance["cumulative_cost"] > 0
        ]["cumulative_cost"].sum()
        performance.loc["portfolio", "market_value"] = performance["market_value"].sum()
        performance.loc["portfolio", "return"] = performance["return"].sum()
        performance.loc["portfolio", "realized"] = performance["realized"].sum()
        performance.loc["portfolio", "unrealized"] = performance["unrealized"].sum()

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

    def calc_transaction_metrics(self, tx_df, price_history=None, other_fields=None):
        """Calculate metrics on transactions DataFrame.

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
        enhance_transactions : DataFrame
            DataFrame containing updated metrics
        """
        if other_fields is None:
            other_fields = []

        tx_df = tx_df.copy()
        transactions = tx_df[tx_df["units"] != 0]
        tickers = list(transactions["ticker"].unique())

        if price_history is None:
            price_history = self.price_history

        price_history = price_history[price_history["ticker"].isin(tickers)]

        tx_df = (
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

        # cumulative amounts
        tx_df["cumulative_units"] = tx_df.groupby("ticker")["units"].transform(
            pd.Series.cumsum
        )
        tx_df["cumulative_cost"] = tx_df.groupby("ticker")["cost"].transform(
            pd.Series.cumsum
        )

        # average price
        tx_df = tx_df.groupby("ticker").apply(self._calc_average_price)

        # market value
        tx_df["market_value"] = tx_df["cumulative_units"] * tx_df["last_price"]

        # return
        tx_df["return"] = tx_df["market_value"] - tx_df["cumulative_cost"]

        tx_df["unrealized"] = tx_df["market_value"] - (
            tx_df["average_price"] * tx_df["cumulative_units"]
        )

        tx_df["realized"] = tx_df["return"] - tx_df["unrealized"]

        # fill in other_fields null values
        for field in other_fields:
            tx_df[field] = tx_df[field].replace(0, np.nan)
            tx_df[field] = tx_df.groupby(["ticker"])[field].apply(
                lambda x: x.ffill().bfill()
            )

        # sort values
        tx_df = tx_df.sort_values(by=["ticker", "date"], ignore_index=True)

        enhance_transactions = tx_df

        return enhance_transactions

    def _get_transactions(self, only_tickers=None, filter_type=None, other_fields=None):
        """Get the transactions made.

        Parameters
        ----------
        tickers : list (optional)
            list of tickers to only include
        filter_type : list (optional)
            list of strings to exclude out of `type` field.
            e.g. a dividend type may not want to be included in total
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
        if other_fields is None:
            other_fields = []

        cols = ["date", "ticker", "type", "units", "cost"] + other_fields
        transactions = pd.read_excel(self.file, engine="openpyxl")
        transactions = transactions[cols]
        transactions = transactions[~transactions["type"].isin(filter_type)]

        # handle multiple transactions on same day by grouping
        transactions = (
            transactions.groupby(by=["date", "ticker", "type"] + other_fields)
            .sum()
            .reset_index()
        )

        transactions["date"] = pd.to_datetime(transactions["date"], format="%d/%m/%Y")
        transactions["sale_price"] = transactions["cost"] / transactions["units"]

        transactions = transactions[~transactions["ticker"].isin(self.blacklist)]

        if only_tickers:
            transactions = transactions[transactions["ticker"].isin(only_tickers)]

        return transactions

    def _get_price_history(self):
        """Get the history of prices.

        Returns
        ----------
        price_history : DataFrame
            the price history
        """
        tickers = [tick for tick in self.tickers if tick not in self.funds]
        if self.funds:
            print(
                f"Did not get price info for {self.funds} and will use transaction"
                " price to develop price history, since they are funds and not"
                " available in stock exchanges"
            )
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
        for fund in self.funds:
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

        price_history = price_history.sort_values(["ticker", "date"])

        return price_history

    def _get_transactions_history(self, only_tickers=None, other_fields=None):
        """Get the history of transcations by merging transaction and price history.

        Parameters
        ----------
        only_tickers : list (optional)
            list of tickers to only include
        other_fields : list (optional)
            additional fields to include

        Returns
        ----------
        transactions_history : DataFrame
            the price history of transactions
        """
        if only_tickers is None:
            only_tickers = []
        if other_fields is None:
            other_fields = []

        transactions = self.transactions

        transactions_history = self.calc_transaction_metrics(
            transactions, other_fields=other_fields
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

    def _get_return_pct(self, ticker, date, tx_df=None):
        """Get the dollar weighted return of a ticker.

        Parameters
        ----------
        ticker : str
            ticker that will be used to calculate metric
        date : date
            date on which to perform the returns as of
        tx_df : DataFrame
            dataframe to get return percent from
        Returns
        ----------
        return_pct : float
            the dollar weighted return of ticker
        """
        if tx_df is None:
            tx_df = self.transactions_history
        transactions = tx_df[tx_df["units"] != 0]

        # get the current price and transactions
        if ticker == "portfolio":
            current_price = tx_df[tx_df["date"] == date]
            ticker_transactions = transactions.copy()

        else:
            current_price = tx_df[(tx_df["ticker"] == ticker) & (tx_df["date"] == date)]
            ticker_transactions = transactions[
                (transactions["ticker"] == ticker) & (transactions["date"] <= date)
            ].copy()

        # combine the current price and transactions
        current_price = current_price[["date", "ticker", "units", "market_value"]]
        ticker_transactions["market_value"] = ticker_transactions["cost"] * -1
        ticker_transactions = pd.concat(
            [ticker_transactions, current_price], ignore_index=True
        )

        # makes sure that ticker had transactions both negative
        # and positive to calculate IRR
        if (
            not min(ticker_transactions["market_value"])
            < 0
            < max(ticker_transactions["market_value"])
        ):
            return_pct = np.NaN

        else:

            return_pct = xirr(
                ticker_transactions["date"], ticker_transactions["market_value"]
            )

            # times where IRR can't be calculated
            if return_pct is None:
                return_pct = np.NaN

            return_pct = min(return_pct, 1000)

        return return_pct

    def _get_return_pcts(self, date=None, tx_df=None):
        """Get the dollar weighted return of transactions.

        Parameters
        ----------
        date : date (optional)
            date on which to perform the returns as of
        tx_df : DataFrame
            dataframe to get return percent from

        Returns
        ----------
        return_pcts : DataFrame
            dollar weighted returns of all transactions
        """
        if date is None:
            date = self._max_date
        if tx_df is None:
            tx_df = self.transactions_history

        tickers = list(tx_df["ticker"].unique())

        return_pcts = pd.DataFrame()

        # get return of each ticker
        for ticker in tickers:
            ticker_return = self._get_return_pct(ticker=ticker, date=date, tx_df=tx_df)

            return_pcts = pd.concat(
                [
                    return_pcts,
                    pd.DataFrame({"ticker": [ticker], "return_pct": ticker_return}),
                ]
            )

        # get portfolio return
        portfolio_return = self._get_return_pct(
            ticker="portfolio", date=date, tx_df=tx_df
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

    def _get_portfolio_view(self, tx_df=None):
        """Get the return of the portfolio over time.

        Useful for plotting returns visually.

        Parameters
        ----------
        tx_df : DataFrame
            dataframe to get return percent from

        Returns
        ----------
        portfolio_view : DataFrame
        """
        if tx_df is None:
            tx_df = self.transactions_history
        portfolio_col = ["ticker", "date", "return"]
        portfolio_view = tx_df[portfolio_col]
        portfolio_view = portfolio_view.pivot_table(
            index="date", columns="ticker", values="return", aggfunc="sum"
        )
        portfolio_view["portfolio"] = portfolio_view.sum(axis=1)

        return portfolio_view

    def _get_cost_view(self, tx_df=None):
        """Get the cost of the portfolio over time.

        Useful for plotting cost visually.

        Parameters
        ----------
        tx_df : DataFrame
            dataframe to get return percent from

        Returns
        ----------
        cost_view : DataFrame
        """
        if tx_df is None:
            tx_df = self.transactions_history
        cost_col = ["ticker", "date", "cumulative_cost"]
        cost_view = tx_df[cost_col]
        cost_view = cost_view.pivot_table(
            index="date", columns="ticker", values="cumulative_cost", aggfunc="sum"
        )
        cost_view["portfolio"] = cost_view.sum(axis=1)
        cost_view = cost_view.round(2)

        return cost_view
