"""Market Screeners.

Provides market screeners
"""

import logging
import pandas as pd
import requests

from bs4 import BeautifulSoup

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


def most_active(count=25):
    """Provide a dataframe of the most active stocks for the most recent trading day.

    [Source: Yahoo]

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

    url = "https://finance.yahoo.com/screener/predefined/most_actives?count=50"

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

    most_active["vol_delta"] = most_active["volume"] / most_active["avg_vol_3_month"]
    most_active["vol_price"] = most_active["volume"] * most_active["price_intraday"]
    most_active = most_active.sort_values("vol_price", ascending=False)

    return most_active


def insider_activity(ticker):
    """Get insider activity.

    [Source: Business Insider]

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
