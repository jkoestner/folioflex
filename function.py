import pandas as pd
import yfinance as yf
import os

from datetime import datetime
from pages import layouttab

pd.options.display.float_format = "{:,.2f}".format


def sector_query():
    """Provides the sector historical stock prices

    Returns
    -------
    sector_close : dataframe
       provides the list of prices for historical prices
    """

    sector_close = yf.download(layouttab.sector_list, start="2018-01-01")

    return sector_close["Adj Close"]


# this is based on work done on medium:
# https://towardsdatascience.com/create-a-dashboard-to-track-anything-with-plotly-and-dash-f9a5234d548b
# the github project:
# https://github.com/fnneves/portfolio_tracker_medium
def get_portfolio_and_transaction(tx_file):
    def clean_header(df):
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(".", "")
            .str.replace("(", "")
            .str.replace(")", "")
            .str.replace(" ", "_")
            .str.replace("_/_", "/")
        )

    def clean_index(df, lvl):
        idx = df.columns.levels[lvl]
        idx = (
            idx.str.lower()
            .str.replace(".", "")
            .str.replace("(", "")
            .str.replace(")", "")
            .str.replace(" ", "_")
            .str.replace("_/_", "/")
        )
        df.columns.set_levels(idx, level=lvl, inplace=True)

        return df

    # transaction history
    print("reading '{}'".format(tx_file))
    tx_col = ["date", "ticker", "units"]
    tx_df = pd.read_excel(tx_file, engine="openpyxl")
    tx_df = tx_df[tx_col]
    tx_df["date"] = pd.to_datetime(tx_df["date"], format="%d/%m/%Y")

    # some tickers may have been delisted. need to blacklist them here
    blacklist = ["VSLR", "HTZ"]
    tx_df = tx_df[~tx_df["ticker"].isin(blacklist)]
    tickers = list(tx_df["ticker"].unique())
    print("You traded {} different stocks".format(len(tickers)))

    # price history
    startdate = datetime(2020, 1, 1)

    px_df = yf.download(tickers, start=startdate)
    clean_index(df=px_df, lvl=0)
    px_df.index.rename("date", inplace=True)
    px_df.columns.rename("measure", level=0, inplace=True)
    px_df.columns.rename("ticker", level=1, inplace=True)

    # stacking px_df
    stack_px_df = px_df.stack(level="ticker")
    stack_px_df.index = stack_px_df.index.swaplevel("date", "ticker")
    stack_px_df.sort_index(axis=0, level="ticker", inplace=True)
    stack_px_df = stack_px_df.reset_index()
    px_col = ["ticker", "date", "adj_close"]
    stack_px_df = stack_px_df[px_col]

    # add close price, latest price to transaction data
    tx_df = pd.merge(tx_df, stack_px_df, how="left", on=["date", "ticker"])
    tx_df["cost"] = tx_df["units"] * tx_df["adj_close"]
    px_last = stack_px_df.sort_values("date").groupby("ticker").tail(1)
    px_last.rename(columns={"adj_close": "last"}, inplace=True)
    px_last = px_last[["ticker", "last"]]
    tx_df = pd.merge(tx_df, px_last, how="left", on=["ticker"])
    tx_df.rename(columns={"adj_close": "transaction_price"}, inplace=True)
    tx_df = tx_df.sort_values("date")
    tx_df = tx_df.round(2)

    # adding transaction values columns to px_df
    stack_px_df = pd.merge(
        stack_px_df,
        tx_df[["date", "ticker", "units", "cost"]],
        how="outer",
        on=["date", "ticker"],
    ).fillna(0)
    stack_px_df["cml_units"] = stack_px_df.groupby("ticker")["units"].transform(
        pd.Series.cumsum
    )
    stack_px_df["cml_cost"] = stack_px_df.groupby("ticker")["cost"].transform(
        pd.Series.cumsum
    )
    stack_px_df["mkt_value"] = stack_px_df["cml_units"] * stack_px_df["adj_close"]
    stack_px_df["gl"] = stack_px_df["mkt_value"] - stack_px_df["cml_cost"]

    # portfolio value
    portfolio_col = ["ticker", "date", "gl"]
    portfolio = stack_px_df[portfolio_col]
    portfolio = portfolio.pivot(index="date", columns="ticker", values="gl")
    portfolio["portfolio"] = portfolio.sum(axis=1)

    # cost value
    cost_col = ["ticker", "date", "cml_cost"]
    cost = stack_px_df[cost_col]
    cost = cost.pivot(index="date", columns="ticker", values="cml_cost")
    cost["portfolio"] = cost.sum(axis=1)
    cost = cost.round(2)

    # performance
    performance = tx_df.groupby("ticker").agg(["sum"])
    performance = performance.droplevel(1, axis="columns")
    performance["mkt_value"] = performance["units"] * performance["last"]
    performance.loc["portfolio"] = 0
    performance.loc["portfolio"]["cost"] = performance[performance["cost"] > 0][
        "cost"
    ].sum()
    performance.loc["portfolio"]["mkt_value"] = performance["mkt_value"].sum()
    performance["return"] = performance["mkt_value"] - performance["cost"]
    performance["return%"] = performance["mkt_value"] / performance["cost"] - 1
    performance = performance.reset_index()
    performance = performance.round(2)
    performance["return%"] = performance["return%"].astype(float).map("{:.1%}".format)
    performance["cost"] = performance["cost"].astype(float).map("{:,.2f}".format)
    performance["mkt_value"] = (
        performance["mkt_value"].astype(float).map("{:,.2f}".format)
    )
    performance["return"] = performance["return"].astype(float).map("{:,.2f}".format)

    return tx_df, portfolio, performance, cost
