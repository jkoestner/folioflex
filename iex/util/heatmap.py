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
    sp500 = get_sp500()

    sp500_df = pd.DataFrame()
    temp_df = pd.DataFrame()
    for i in [100, 200, 300, 400, 500, 600]:
        start = i - 100
        sp500_i = sp500.iloc[start:i]
        iex_query = (
            "https://cloud.iexapis.com/stable/stock/market/batch?symbols="
            + ",".join(sp500_i["symbol"])
            + "&types=quote&token="
            + constants.iex_api_live
        )
        temp_df = pd.read_json(iex_query, orient="index")
        temp_df = pd.json_normalize(temp_df["quote"])
        sp500_df = pd.concat([sp500_df, temp_df])

    df = pd.merge(
        sp500_df[["changePercent", "marketCap", "symbol"]],
        sp500,
        how="outer",
        on=["symbol"],
    )
    df["changePercent"] = (
        df["changePercent"].replace("[\\$,]", "", regex=True).astype(float)
    )
    df["marketCap"] = df["marketCap"].fillna(1)

    fig = px.treemap(
        df,
        path=[px.Constant("all"), "sector", "symbol"],
        values="marketCap",
        color="changePercent",
        color_continuous_scale="armyrose_r",
        color_continuous_midpoint=0,
        hover_data={"changePercent": ":.2p"},
    )

    return fig


def get_sp500():
    """Provide sp500 tickers with sectors.

    Returns
    -------
    sp500 : DataFrame
       sp500 tickers and sectors
    """
    url = r"https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    context = ssl._create_unverified_context()
    response = request.urlopen(url, context=context)
    html = response.read()

    sp500 = pd.read_html(html)[0][["Symbol", "GICS Sector"]]

    sp500.rename(
        columns={
            "GICS Sector": "sector",
            "Symbol": "symbol",
        },
        inplace=True,
    )

    return sp500
