"""
Creates wrappers for different data sources.

The data sources or api may change or become obsolete. This wrapper abstracts the data
from the larger portfolio project, and allows easier integration.

"""

import ssl
from datetime import datetime, time, timedelta
from io import StringIO
from urllib import request

import fredapi
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

from folioflex.portfolio import helper
from folioflex.utils import config_helper, custom_logger

pd.options.display.float_format = "{:,.2f}".format

logger = custom_logger.setup_logging(__name__)


class BLS:
    """
    Wrapper for bureau of labor statistics.

    Class that provides functions that use data from bureau of labor statistics.
    https://www.bls.gov/cpi/

    The api documentation can be found here and using v1 so don't need an api key:
    https://www.bls.gov/developers/api_signature.htm
    """

    def __init__(self):
        pass

    def get_cpi(self):
        """
        Get the latest CPI information.

        Returns
        -------
        cpi : dict
            dictionary of CPI information

        """
        # Series ID for CPI-U (U.S. city average, All items)
        series_id = "CUSR0000SA0"
        url = f"https://api.bls.gov/publicAPI/v1/timeseries/data/{series_id}"
        response = requests.get(url)

        data = response.json()

        if data["status"] != "REQUEST_SUCCEEDED":
            logger.warning(data["message"])
            return {"cpi": None, "year": None, "month": None}

        # Process the data as needed
        cpi = {
            "cpi": (
                float(data["Results"]["series"][0]["data"][0]["value"])
                / float(data["Results"]["series"][0]["data"][12]["value"])
            ),
            "year": data["Results"]["series"][0]["data"][0]["year"],
            "month": data["Results"]["series"][0]["data"][0]["periodName"],
        }
        return cpi


class Finviz:
    """
    Wrapper for FinViz data.

    Class that provides functions that use data from FinViz data.

    """

    def __init__(self):
        pass

    def get_heatmap_data(self, timeframe="day"):
        """
        Get heatmap data from finviz.

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
            timeout=10,
        )
        r.raise_for_status()

        df_change = pd.DataFrame.from_dict(r.json()["nodes"], orient="index")
        df_change.columns = ["return_pct"]
        df_change["return_pct"] = df_change["return_pct"] / 100

        # get sector and market cap data
        r2 = requests.get(
            "https://finviz.com/maps/sec.json?rev=316",
            headers=_get_header(),
            timeout=10,
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


class Fred:
    """
    Wrapper for federal reserve data.

    Class that provides functions that use data from federal reserve.

    The api documentation can be found here:
    https://fred.stlouisfed.org/docs/api/fred/
    """

    def __init__(self):
        pass

    def get_summary(self):
        """
        Get a summary of FRED data.

        Returns
        -------
        fred_summary : dict
            provides dictionary of FRED data

        """
        fred_lkup = {
            "recession": "RECPROUSM156N",
            "unemployment": "UNRATE",
            "inflation": "CPIAUCSL",
            "fed_funds": "FEDFUNDS",
            "housing_starts": "HOUST",
            "10_year": "DGS10",
        }
        fred_summary = {
            "recession": None,
            "unemployment": None,
            "inflation": None,
            "fed_funds": None,
            "housing_starts": None,
            "10_year": None,
        }
        if config_helper.FRED_API is None:
            logger.warning(
                "No FRED API key found you can sign up free here http://research.stlouisfed.org/fred2/"
            )
            return fred_summary
        fred = fredapi.Fred(api_key=config_helper.FRED_API)
        for key, value in fred_lkup.items():
            fred_summary[key] = fred.get_series(value).iloc[-1]

        return fred_summary


class TradingView:
    """
    Wrapper for Trading View api.

    Class that provides functions that use data from TradingView.
    https://www.tradingview.com

    """

    def __init__(self):
        pass

    def get_economic_calendar(self, to_date=None, from_date=None, minImportance=1):
        """
        Get the latest economic calendar.

        This is sourced from the following site:
        https://www.tradingview.com/economic-calendar/

        Parameters
        ----------
        to_date : str (optional)
            the end date of the calendar - format YYYY-MM-DD
            default is today
        from_date : str (optional)
            the start date of the calendar - format YYYY-MM-DD
            default is 7 days ago
        minImportance : int (optional)
            the minimum importance of the event
            default is 1

        Returns
        -------
        calendar : DataFrame
            DataFrame of economic calendar

        """

        def normalize_date(date, time):
            # Format the date and time in ISO 8601 format
            normalize_date = datetime.combine(date, time)
            normalize_date = normalize_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            return normalize_date

        to_date = (
            datetime.utcnow() + timedelta(days=7)
            if to_date is None
            else datetime.strptime(to_date, "%Y-%m-%d")
        )
        from_date = (
            to_date - timedelta(days=14)
            if from_date is None
            else datetime.strptime(from_date, "%Y-%m-%d")
        )

        to_date = normalize_date(to_date, time(23, 0, 0, 0))
        from_date = normalize_date(from_date, time(0, 0, 0, 0))

        url = "https://economic-calendar.tradingview.com/events"
        payload = {
            "from": from_date,
            "to": to_date,
            "countries": ["US"],
            "minImportance": minImportance,
        }
        # headers are now required as 07/24/2024
        headers = {"Origin": "https://us.tradingview.com"}
        response = requests.get(url, params=payload, headers=headers).json()
        calendar = pd.DataFrame(response["result"])
        calendar["date"] = pd.to_datetime(calendar["date"]).dt.date
        # select columns to keep
        calendar = calendar[
            [
                "date",
                "title",
                "indicator",
                "source",
                "period",
                "actual",
                "previous",
                "forecast",
                "comment",
                "importance",
                "country",
            ]
        ]

        return calendar


class Web:
    """
    Wrapper for web data.

    Class that provides functions that use data from web data.

    """

    def __init__(self):
        pass

    def get_sp500_tickers(self):
        """
        Provide sp500 tickers with sectors.

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

        sp500_tickers = sp500_tickers.rename(
            columns={
                "GICS Sector": "sector",
                "Symbol": "ticker",
            },
        )

        return sp500_tickers

    def insider_activity(self, ticker):
        """
        Get insider activity.

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
        response = requests.get(url, headers=_get_header(), timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        d_insider = {}
        l_insider_vals = []
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
                l_insider_vals = []

        df_insider = pd.DataFrame.from_dict(
            d_insider,
            orient="index",
            columns=["Date", "Shares Traded", "Shares Held", "Price", "Type", "Option"],
        )

        df_insider["Date"] = pd.to_datetime(df_insider["Date"])

        l_names = []
        # get name
        s_names = soup.findAll("a", {"onclick": "silentTrackPI()"})
        l_names = [s_name.text.strip() for s_name in s_names]
        df_insider["Insider"] = l_names

        df_insider = df_insider.set_index("Date")
        df_insider = df_insider.sort_index(ascending=False)
        return df_insider


def _get_header():
    """
    Get header for requests.

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
    """
    Convert string to number.

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


class Yahoo:
    """
    Wrapper for yahoo finance data.

    Class that provides functions that use data from yahoo finance.
    """

    def __init__(self):
        pass

    def stock_history(self, tickers, min_year):
        """
        Get stock history data for a set of tickers.

        Parameters
        ----------
        tickers : list
            symbols to get data for
        min_year : int
            the minimum year to get data for

        Returns
        -------
        stock_data : DataFrame
            the stock history
               - ticker
               - date
               - last price

        """
        stock_data = yf.download(
            tickers,
            start=datetime(min_year, 1, 1),
            end=datetime(2100, 1, 1),
            actions=True,  # get dividends and stock splits
        )
        stock_data = self._clean_index(clean_df=stock_data, lvl=0, tickers=tickers)
        stock_data.index = stock_data.index.rename("date")
        stock_data.columns = stock_data.columns.rename("measure", level=0)
        stock_data.columns = stock_data.columns.rename("ticker", level=1)

        stock_data = stock_data.stack(level="ticker", future_stack=True)
        stock_data.index = stock_data.index.swaplevel("date", "ticker")
        stock_data = stock_data.sort_index(axis=0, level="ticker")
        stock_data = stock_data.reset_index()
        cols = ["ticker", "date", "adj_close", "stock_splits"]
        stock_data = stock_data[cols]
        stock_data = stock_data.rename(columns={"adj_close": "last_price"})
        stock_data["date"] = helper.convert_date_to_timezone(
            stock_data["date"], timezone=None
        )

        return stock_data

    def news(self, ticker):
        """
        Get the news for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        -------
        news : DataFrame
            provides news articles on ticker

        """
        yf_ticker = yf.Ticker(ticker)
        news = pd.DataFrame(yf_ticker.news)
        news = news.drop(columns=["thumbnail", "uuid"])
        news["providerPublishTime"] = pd.to_datetime(
            news["providerPublishTime"], unit="s"
        )

        return news

    def info(self, ticker):
        """
        Get the info for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        -------
        info : DataFrame
            provides info on ticker

        """
        yf_ticker = yf.Ticker(ticker)
        info = pd.DataFrame([yf_ticker.info])
        info = info.T
        info = info.rename(columns={0: "value"})

        return info

    def fast_info(self, ticker):
        """
        Get the info for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        -------
        fast_info : dict
            provides dictionary of info on ticker

        """
        fast_info = yf.Ticker(ticker).fast_info

        return fast_info

    def quote(self, ticker):
        """
        Get the quote for ticker.

        Parameters
        ----------
        ticker : str
            symbol to get data for

        Returns
        -------
        quote : DataFrame
            provides quote on ticker

        """
        d = yf.Ticker(ticker).fast_info
        keys = list(d.keys())
        values = list(d.values())

        # Create a DataFrame from these lists
        quote = pd.DataFrame({"Keys": keys, "Values": values})
        quote = quote.set_index("Keys")

        return quote

    def most_active(self, count=25):
        """
        Provide a dataframe of the most active stocks for the most recent trading day.

        Parameters
        ----------
        count : int (default=25)
            number of most active stocks to return

        Returns
        -------
        most_active : DataFrame
        DataFrame of most active stocks

        """
        min_count = 0
        max_count = 101
        if count <= min_count or count >= max_count:
            logger.warning(
                f"Count should be between 1 and 100 and the count was {count}"
            )

        url = (
            f"https://finance.yahoo.com/screener/predefined/most_actives?count={count}"
        )

        response = requests.get(url, headers=_get_header(), timeout=10)
        most_active = pd.read_html(StringIO(response.text))[0]

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
        """
        Get the percentage change of a stock over a given number of days.

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
        # fixing the date to the last valid stock date
        end_date = helper.most_recent_stock_date()
        # yfinance is exclusive of end date so add 1 day
        # https://github.com/ranaroussi/yfinance/wiki/Ticker#history
        end_date = end_date + timedelta(days=1)
        start_date = end_date - timedelta(days=days + 1)
        start_date = helper.check_stock_dates(start_date, fix=True)["fix_tx_df"][
            "date"
        ][0]
        end_date = end_date.strftime("%Y-%m-%d")
        start_date = start_date.strftime("%Y-%m-%d")

        data = yf.download(ticker, start=start_date, end=end_date)

        # Extract the adjusted close price from one year ago and the most recent price
        start_price = data["Adj Close"].iloc[0]
        end_price = data["Adj Close"].iloc[-1]

        # Calculate the change percentage
        change_percent = (end_price - start_price) / start_price

        return change_percent

    def get_sma(self, ticker, days=365):
        """
        Get the percentage change of a stock over a given number of days.

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
        """
        Clean the index of DataFrame.

        Parameters
        ----------
        clean_df : DataFrame
            the dataframe on which to clean
        lvl : int
            the level of index to clean
        tickers : list (optional)
            when only using 1 ticker that ticker needs to be passed to create a
            multiIndex column

        Returns
        -------
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
