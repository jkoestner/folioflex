import pandas as pd
import yfinance as yf
from pages import layouttab


def Query():
    """Provides the sector historical stock prices

    Returns
    -------
    sector_close : dataframe
       provides the list of prices for historical prices
    """

    sector_close = yf.download(layouttab.sector_list, start="2018-01-01")

    return sector_close["Adj Close"]
