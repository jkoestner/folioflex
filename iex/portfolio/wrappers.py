"""
Creates wrappers for different data sources.

The data sources or api may change or become obsolete. This wrapper abstracts the data
from the larger portfolio project, and allows easier integration.

"""

import logging
import pandas as pd
import yfinance as yf

from datetime import datetime

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


class Yahoo:
    """Wrapper for yahoo finance data.

    Class that provides functions that use data from yahoo finance.
    """

    def __init__(self):
        pass

    def stock_history(self, tickers, min_year):
        """Get stock history data for a set of tickers.

        Parameters
        ----------
        tickers : list
            symbols to get data for
        min_year : int
            the minimum year to get data for

        Returns
        ----------
        stock_data : DataFrame
            the stock history
               - ticker
               - date
               - last price
        """
        stock_data = yf.download(
            tickers, start=datetime(min_year, 1, 1), end=datetime(2100, 1, 1)
        )
        self._clean_index(clean_df=stock_data, lvl=0, tickers=tickers)
        stock_data.index.rename("date", inplace=True)
        stock_data.columns.rename("measure", level=0, inplace=True)
        stock_data.columns.rename("ticker", level=1, inplace=True)

        stock_data = stock_data.stack(level="ticker")
        stock_data.index = stock_data.index.swaplevel("date", "ticker")
        stock_data.sort_index(axis=0, level="ticker", inplace=True)
        stock_data = stock_data.reset_index()
        cols = ["ticker", "date", "adj_close"]
        stock_data = stock_data[cols]
        stock_data.rename(columns={"adj_close": "last_price"}, inplace=True)

        return stock_data

    def news(self, ticker):
        """Get the news for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        ----------
        news : DataFrame
            provides news articles on ticker
        """
        yf_ticker = yf.Ticker(ticker)
        news = pd.DataFrame(yf_ticker.news)
        news.drop(columns=["thumbnail", "uuid"], inplace=True)
        news["providerPublishTime"] = pd.to_datetime(
            news["providerPublishTime"], unit="s"
        )

        return news

    def info(self, ticker):
        """Get the info for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        ----------
        info : DataFrame
            provides info on ticker
        """
        yf_ticker = yf.Ticker(ticker)
        info = pd.DataFrame([yf_ticker.info])
        info = info.T

        return info

    def quote(self, ticker):
        """Get the quote for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        ----------
        quote : DataFrame
            provides quote on ticker
        """
        d = yf.Ticker(ticker).get_fast_info
        keys = list(d.keys())
        values = list(d.values())

        # Create a DataFrame from these lists
        quote = pd.DataFrame({"Keys": keys, "Values": values})

        return quote

    def _clean_index(self, clean_df, lvl, tickers):
        """Clean the index of DataFrame.

        Parameters
        ----------
        clean_df : DataFrame
            the dataframe on which to clean
        lvl : int
            the level of index to clean
        tickers : list (optional)
            when only using 1 ticker that ticker needs to be passed to create a multiIndex column

        Returns
        ----------
        clean_df : DataFrame
            a clean DataFrame
        """
        if clean_df.columns.nlevels == 1:
            clean_df.columns = pd.MultiIndex.from_product([clean_df.columns, tickers])

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
