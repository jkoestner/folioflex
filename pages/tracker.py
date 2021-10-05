import pandas as pd
import yfinance as yf
import os

from datetime import datetime

import dash_table
from dash import dcc
from dash import html
from pages import utils

# this is based on work done on medium:
# https://towardsdatascience.com/create-a-dashboard-to-track-anything-with-plotly-and-dash-f9a5234d548b
# the github project:
# https://github.com/fnneves/portfolio_tracker_medium


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
tx_path = r"/app/files/transactions.xlsx"
print("reading '{}'".format(tx_path))
tx_col = ["date", "ticker", "units"]
tx_df = pd.read_excel(tx_path, engine="openpyxl")
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
tx_df = tx_df.sort_values("date")

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
portfolio = portfolio.pivot(index="date", columns="ticker", values="gl").reset_index()
portfolio["portfolio"] = portfolio.sum(axis=1)

# Creating the dash app
layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                # graph
                dcc.Graph(
                    id="Tracker-Graph",
                ),
                # range slider
                html.P(
                    [
                        html.Label("Time Period"),
                        dcc.RangeSlider(
                            id="track_slider",
                            tooltip="always_visible",
                        ),
                    ],
                    style={
                        "width": "80%",
                        "fontSize": "20px",
                        "padding-left": "100px",
                        "display": "inline-block",
                    },
                ),
                html.P(),
                html.P(),
                # creating table for sector perfomance
                html.Label("Transactions"),
                dash_table.DataTable(
                    id="transaction-table",
                    sort_action="native",
                    columns=[{"name": i, "id": i} for i in tx_df.columns],
                    data=tx_df.to_dict("records"),
                ),
                html.P(),
            ],
            className="row",
        ),
    ]
)
