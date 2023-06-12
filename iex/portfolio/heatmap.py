"""Heatmap for app.

Provides the heatmap
"""

import pandas as pd
import plotly.express as px
import ssl

from urllib import request

from iex.util import constants


def get_heatmap(portfolio=None, lookback=None):
    """Provide figure for heatmap.

    Parameters
    ----------
    portfolio : Portfolio Class (default is None)
        portfolio to get heatmap for, if None use sp500
    lookback : int (optional)
        number of days to lookback

    Returns
    -------
    fig : Figure
       heatmap figure
    """
    if portfolio is None:
        returns = get_sp500_returns()
        color = "return_pct"
    else:
        returns = portfolio.get_performance(lookback=lookback)
        returns = returns.reset_index()
        # remove portfolio and benchmark
        returns = returns.loc[
            ~returns["ticker"].isin(["portfolio"])
            & ~returns["ticker"].str.contains("benchmark")
        ]
        color = "simple_return_pct"

    returns = returns[[color, "market_value", "ticker"]]
    sp500_tickers = get_sp500_tickers()
    returns = pd.merge(
        returns,
        sp500_tickers,
        how="outer",
        on=["ticker"],
    )
    returns["sector"] = returns["sector"].fillna("Other")
    returns = returns[returns["market_value"] > 0]  # remove nulls/zero in market cap

    fig = px.treemap(
        returns,
        path=[px.Constant("all"), "sector", "ticker"],
        values="market_value",
        color=color,
        color_continuous_scale="armyrose_r",
        color_continuous_midpoint=0,
        hover_data={color: ":.2p"},
    )

    return fig


def get_sp500_tickers():
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


def get_sp500_returns():
    """Get the sp500 returns used in heatmap.

    Returns
    -------
    sp500_returns : DataFrame
       sp500 returns
    """
    sp500_tickers = get_sp500_tickers()

    # iterate through ticker list. iex restricts results to 100
    sp500_returns = pd.DataFrame()
    temp_df = pd.DataFrame()
    for i in [100, 200, 300, 400, 500, 600]:
        start = i - 100
        iex_query = (
            "https://cloud.iexapis.com/stable/stock/market/batch?symbols="
            + ",".join(sp500_tickers.iloc[start:i]["ticker"])
            + "&types=quote&token="
            + constants.iex_api_live
        )
        temp_df = pd.read_json(iex_query, orient="index")
        temp_df = pd.json_normalize(temp_df["quote"])
        sp500_returns = pd.concat([sp500_returns, temp_df])

    sp500_returns["changePercent"] = (
        sp500_returns["changePercent"].replace("[\\$,]", "", regex=True).astype(float)
    )
    # nulls/zero in market cap will not allow aggregation, replacing with 1
    sp500_returns["marketCap"] = sp500_returns["marketCap"].fillna(1)
    sp500_returns["marketCap"] = sp500_returns["marketCap"].replace(
        to_replace=0, value=1
    )

    sp500_returns.rename(
        columns={
            "changePercent": "return_pct",
            "marketCap": "market_value",
            "symbol": "ticker",
        },
        inplace=True,
    )

    return sp500_returns
