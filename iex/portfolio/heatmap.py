"""Heatmap for app.

Provides the heatmap
"""

import pandas as pd
import plotly.express as px

from iex.portfolio.wrappers import Finviz, Web


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
        returns = Finviz().get_heatmap_data()
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
    sp500_tickers = Web().get_sp500_tickers()
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
