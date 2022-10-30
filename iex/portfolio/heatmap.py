"""Heatmap for app.

Provides the heatmap
"""

import pandas as pd
import plotly.express as px
import ssl

from urllib import request

from iex.util import constants


def get_heatmap():
    """Provide figure for heatmap.

    Returns
    -------
    fig : Figure
       heatmap figure
    """
    sp500_tickers = get_sp500_tickers()

    # iterate through ticker list. iex restricts results to 100
    sp500_returns = pd.DataFrame()
    temp_df = pd.DataFrame()
    for i in [100, 200, 300, 400, 500, 600]:
        start = i - 100
        iex_query = (
            "https://cloud.iexapis.com/stable/stock/market/batch?symbols="
            + ",".join(sp500_tickers.iloc[start:i]["symbol"])
            + "&types=quote&token="
            + constants.iex_api_live
        )
        temp_df = pd.read_json(iex_query, orient="index")
        temp_df = pd.json_normalize(temp_df["quote"])
        sp500_returns = pd.concat([sp500_returns, temp_df])

    sp500 = pd.merge(
        sp500_returns[["changePercent", "marketCap", "symbol"]],
        sp500_tickers,
        how="outer",
        on=["symbol"],
    )
    sp500["changePercent"] = (
        sp500["changePercent"].replace("[\\$,]", "", regex=True).astype(float)
    )
    # nulls/zero in market cap will not allow aggregation, replacing with 1
    sp500["marketCap"] = sp500["marketCap"].fillna(1)
    sp500["marketCap"] = sp500["marketCap"].replace(to_replace=0, value=1)

    fig = px.treemap(
        sp500,
        path=[px.Constant("all"), "sector", "symbol"],
        values="marketCap",
        color="changePercent",
        color_continuous_scale="armyrose_r",
        color_continuous_midpoint=0,
        hover_data={"changePercent": ":.2p"},
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
            "Symbol": "symbol",
        },
        inplace=True,
    )

    return sp500_tickers
