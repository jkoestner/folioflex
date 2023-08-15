"""
Creates wrappers for different data sources.

The data sources or api may change or become obsolete. This wrapper abstracts the data
from the larger portfolio project, and allows easier integration.

"""

import fredapi
import logging
import pandas as pd
import yfinance as yf
import requests
import ssl

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib import request

from iex.utils import config_helper

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
        info = info.rename(columns={0: "value"})

        return info

    def fast_info(self, ticker):
        """Get the info for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        ----------
        fast_info : dict
            provides dictionary of info on ticker
        """
        fast_info = yf.Ticker(ticker).fast_info

        return fast_info

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
        d = yf.Ticker(ticker).fast_info
        keys = list(d.keys())
        values = list(d.values())

        # Create a DataFrame from these lists
        quote = pd.DataFrame({"Keys": keys, "Values": values})
        quote.set_index("Keys", inplace=True)

        return quote

    def most_active(self, count=25):
        """Provide a dataframe of the most active stocks for the most recent trading day.

        Parameters
        ----------
        count : int (default=25)
            portfolio to get heatmap for, if None use sp500

        Returns
        -------
        most_active : DataFrame
        DataFrame of most active stocks
        """
        if count <= 0 or count >= 101:
            logger.warning("Count should be between 1 and 100")

        url = (
            f"https://finance.yahoo.com/screener/predefined/most_actives?count={count}"
        )

        response = requests.get(url, headers=_get_header())
        most_active = pd.read_html(response.text)[0]

        # lower and use underscores for column names
        most_active.columns = (
            most_active.columns.str.lower()
            .str.replace(".", "", regex=False)
            .str.replace("(", "", regex=False)
            .str.replace(")", "", regex=False)
            .str.replace(" ", "_", regex=False)
            .str.replace("_/_", "/", regex=False)
        )
        cols_keep = [
            "symbol",
            "name",
            "price_intraday",
            "change",
            "%_change",
            "volume",
            "avg_vol_3_month",
            "market_cap",
        ]
        most_active = most_active[cols_keep]

        # update columns
        for var in ["%_change", "volume", "avg_vol_3_month", "market_cap"]:
            most_active[var] = most_active[var].apply(_convert_to_number)

        most_active["vol_delta"] = (
            most_active["volume"] / most_active["avg_vol_3_month"]
        )
        most_active["vol_price"] = most_active["volume"] * most_active["price_intraday"]
        most_active = most_active.sort_values("vol_price", ascending=False)

        return most_active

    def get_change_percent(self, ticker, days=365):
        """Get the percentage change of a stock over a given number of days.

        Parameters
        ----------
        ticker : str
            the ticker symbol of the stock
        days : int (default=365)
            the number of days to go back in time

        Returns
        -------
        change_percent : float
            the percentage change of the stock over the given number of days
        """
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        data = yf.download(ticker, start=start_date, end=end_date)

        # Extract the adjusted close price from one year ago and the most recent price
        start_price = data["Adj Close"].iloc[0]
        end_price = data["Adj Close"].iloc[-1]

        # Calculate the 1-year change percentage
        change_percent = (end_price - start_price) / start_price

        return change_percent

    def get_sma(self, ticker, days=365):
        """Get the percentage change of a stock over a given number of days.

        Parameters
        ----------
        ticker : str
            the ticker symbol of the stock
        days : int (default=365)
            the number of days to go back in time

        Returns
        -------
        sma : float
            the simple moving average
        """
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        data = yf.download(ticker, start=start_date, end=end_date)

        # Calculate the SMA using the rolling method
        sma = data["Close"].mean()

        return sma

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


class Fred:
    """Wrapper for federal reserve data.

    Class that provides functions that use data from federal reserve.

    The api documentation can be found here:
    https://fred.stlouisfed.org/docs/api/fred/
    """

    def __init__(self):
        pass

    def get_summary(self):
        """Get a summary of FRED data.

        Returns
        ----------
        fred_summary : dict
            provides dictionary of FRED data
        """
        fred = fredapi.Fred(api_key=config_helper.FRED_API)
        fred_dict = {
            "recession": "RECPROUSM156N",
            "unemployment": "UNRATE",
            "inflation": "CPIAUCSL",
            "fed_funds": "FEDFUNDS",
            "housing_starts": "HOUST",
        }
        fred_summary = {}
        for key, value in fred_dict.items():
            fred_summary[key] = fred.get_series(value)[-1]

        return fred_summary


class Finviz:
    """Wrapper for FinViz data.

    Class that provides functions that use data from FinViz data.

    """

    def __init__(self):
        pass

    def get_heatmap_data(self, timeframe="day"):
        """Get heatmap data from finviz.

        [Source: FinViz]
        [Snippet Source: OpenBB - function `get_heatmap_data`]

        Parameters
        ----------
        timeframe: str
            Timeframe to get performance for

        Returns
        -------
        pd.DataFrame
            Dataframe of tickers, changes and sectors
        """
        # dict of valid timeframes
        timeframe_map = {
            "day": "",
            "week": "w1",
            "month": "w4",
            "3month": "w13",
            "6month": "w26",
            "year": "w52",
            "ytd": "ytd",
        }

        if timeframe not in timeframe_map:
            logger.warning("{timeframe} is an invalid timeframe")
            return pd.DataFrame()

        # get change percent data
        r = requests.get(
            f"https://finviz.com/api/map_perf.ashx?t=sec&st={timeframe_map[timeframe]}",
            headers=_get_header(),
        )
        r.raise_for_status()

        df_change = pd.DataFrame.from_dict(r.json()["nodes"], orient="index")
        df_change.columns = ["return_pct"]
        df_change["return_pct"] = df_change["return_pct"] / 100

        # get sector and market cap data
        r2 = requests.get(
            "https://finviz.com/maps/sec.json?rev=316",
            headers=_get_header(),
        )
        r2.raise_for_status()

        dfs_list = []
        for sector_dict in r2.json()["children"]:
            for industry_dict in sector_dict["children"]:
                temp = pd.DataFrame(industry_dict["children"])
                temp["sector"] = sector_dict["name"]
                temp["industry"] = industry_dict["name"]
                dfs_list.append(temp)
        dfs = pd.concat(dfs_list, axis=0).reset_index(drop=True)

        # merge dataframes
        dfs = pd.merge(dfs, df_change, left_on="name", right_index=True)
        dfs = dfs.rename(
            columns={
                "name": "ticker",
                "value": "market_value",
                "sector": "sector",
                "industry": "industry",
                "return_pct": "return_pct",
            }
        )
        return dfs


class Web:
    """Wrapper for web data.

    Class that provides functions that use data from web data.

    """

    def __init__(self):
        pass

    def get_sp500_tickers(self):
        """Provide sp500 tickers with sectors.

        Returns
        -------
        sp500_tickers : DataFrame
        sp500 tickers and sectors
        """
        url = r"https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        context = ssl._create_unverified_context()
        response = request.urlopen(url, context=context)
        html = response.read()

        sp500_tickers = pd.read_html(html)[0][["Symbol", "GICS Sector"]]

        sp500_tickers.rename(
            columns={
                "GICS Sector": "sector",
                "Symbol": "ticker",
            },
            inplace=True,
        )

        return sp500_tickers

    def insider_activity(self, ticker):
        """Get insider activity.

        [Source: Business Insider]
        [Snippet Source: OpenBB - function `get_insider_activity`]

        Parameters
        ----------
        ticker : str
            The ticker to get insider activity for

        Returns
        -------
        df_insider : DataFrame
            Insider activity data
        """
        url = f"https://markets.businessinsider.com/stocks/{ticker.lower()}-stock"
        response = requests.get(url, headers=_get_header())
        soup = BeautifulSoup(response.content, "html.parser")

        d_insider = dict()
        l_insider_vals = list()
        for idx, insider_val in enumerate(
            soup.findAll("td", {"class": "table__td text-center"})
        ):
            l_insider_vals.append(insider_val.text.strip())

            # Add value to dictionary
            if (idx + 1) % 6 == 0:
                # Check if we are still parsing insider trading activity
                if "/" not in l_insider_vals[0]:
                    break
                d_insider[(idx + 1) // 6] = l_insider_vals
                l_insider_vals = list()

        df_insider = pd.DataFrame.from_dict(
            d_insider,
            orient="index",
            columns=["Date", "Shares Traded", "Shares Held", "Price", "Type", "Option"],
        )

        df_insider["Date"] = pd.to_datetime(df_insider["Date"])

        l_names = list()
        # get name
        for s_name in soup.findAll("a", {"onclick": "silentTrackPI()"}):
            l_names.append(s_name.text.strip())
        df_insider["Insider"] = l_names

        df_insider = df_insider.set_index("Date")
        df_insider = df_insider.sort_index(ascending=False)
        return df_insider


def _get_header():
    """Get header for requests.

    Returns
    -------
    headers : str
        header for requests
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/58.0.3029.110 Safari/537.3"
    }
    return headers


def _convert_to_number(s):
    """Convert string to number.

    Parameters
    ----------
    s : str
        string to convert to number

    Returns
    -------
    s : float
        float value of string
    """
    s = str(s).strip()
    if s[-1] == "M":  # for million values
        return float(s[:-1]) * 10**6
    elif s[-1] == "B":  # for billion values
        return float(s[:-1]) * 10**9
    elif s[-1] == "T":  # for trillion values
        return float(s[:-1]) * 10**12
    elif s[-1] == "%":  # for percentage values
        return float(s[:-1]) / 100
    else:  # if there's no M, B, or %, then we can simply convert to float
        return float(s)
