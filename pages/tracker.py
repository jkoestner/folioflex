import numpy as np
import pandas as pd
import yfinance as yf

from time import strftime, sleep
from datetime import datetime
from pandas_datareader import data as pdr
from pandas.tseries.offsets import BDay

# this is based on work done on medium:
# https://towardsdatascience.com/create-a-dashboard-to-track-anything-with-plotly-and-dash-f9a5234d548b
# the github project:
# https://github.com/fnneves/portfolio_tracker_medium

# yf.pdr_override() not sure what this does

# simple function to make headers nicer
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


# timestamp for file names
def get_now():
    now = datetime.now().strftime("%Y-%m-%d_%Hh%Mm")
    return now


# read the transactions
transaction_path = r"../files/transactions.xlsx"
print("reading '{}'".format(transaction_path))
all_transactions = pd.read_excel(transaction_path, engine="openpyxl")
all_transactions["date"] = pd.to_datetime(all_transactions["date"], format="%d/%m/%Y")

# some tickers may have been delisted. need to blacklist them here
blacklist = ["VSLR", "HTZ"]
all_transactions = all_transactions[~all_transactions["ticker"].isin(blacklist)]
all_tickers = list(all_transactions["ticker"].unique())
print("You traded {} different stocks".format(len(all_tickers)))


# --------------------- next part ------------------
ly = datetime.today().year - 1
today = datetime.today()
start_sp = datetime(2019, 1, 1)
end_sp = today
start_stocks = datetime(2019, 1, 1)
end_stocks = today
start_ytd = datetime(ly, 12, 31) + BDay(1)


def get(tickers, startdate, enddate):
    def data(ticker):
        return pdr.get_data_yahoo(ticker, start=startdate, end=enddate)

    datas = map(data, tickers)
    return pd.concat(datas, keys=tickers, names=["ticker", "date"])


all_data = get(filt_tickers, start_stocks, end_stocks)
clean_header(all_data)

# saving all stock prices individually to the specified folder
for tick in filt_tickers:
    all_data.loc[tick].to_csv("../files/output/{}_price_hist.csv".format(tick))

# --------------------- next part ------------------
MEGA_DICT = {}  # you have to create it first
min_date = "2020-01-01"  # optional
TX_COLUMNS = ["date", "ticker", "cashflow", "cml_units", "cml_cost", "gain_loss"]
tx_filt = all_transactions[TX_COLUMNS]  # keeping just the most relevant ones for now

for ticker in filt_tickers:
    prices_df = all_data[
        all_data.index.get_level_values("ticker").isin([ticker])
    ].reset_index()
    ## Can add more columns like volume!
    PX_COLS = ["date", "adj_close"]
    prices_df = prices_df[prices_df.date >= min_date][PX_COLS].set_index(["date"])
    # Making sure we get sameday transactions
    tx_df = (
        tx_filt[tx_filt.ticker == ticker]
        .groupby("date")
        .agg(
            {
                "cashflow": "sum",
                "cml_units": "last",
                "cml_cost": "last",
                "gain_loss": "sum",
            }
        )
    )
    # Merging price history and transactions dataframe
    tx_and_prices = pd.merge(
        prices_df, tx_df, how="outer", left_index=True, right_index=True
    ).fillna(0)
    # This is to fill the days that were not in our transaction dataframe
    tx_and_prices["cml_units"] = tx_and_prices["cml_units"].replace(
        to_replace=0, method="ffill"
    )
    tx_and_prices["cml_cost"] = tx_and_prices["cml_cost"].replace(
        to_replace=0, method="ffill"
    )
    tx_and_prices["gain_loss"] = tx_and_prices["gain_loss"].replace(
        to_replace=0, method="ffill"
    )
    # Cumulative sum for the cashflow
    tx_and_prices["cashflow"] = tx_and_prices["cashflow"].cumsum()
    tx_and_prices["avg_price"] = tx_and_prices["cml_cost"] / tx_and_prices["cml_units"]
    tx_and_prices["mktvalue"] = tx_and_prices["cml_units"] * tx_and_prices["adj_close"]
    tx_and_prices = tx_and_prices.add_prefix(ticker + "_")
    # Once we're happy with the dataframe, add it to the dictionary
    MEGA_DICT[ticker] = tx_and_prices.round(3)

# check an individual stock
# MEGA_DICT['RUN'].tail()

# saving it, so we can access it quicker later
MEGA_DF = pd.concat(MEGA_DICT.values(), axis=1)
MEGA_DF.to_csv("../files/output/mega/MEGA_DF_{}.csv".format(get_now()))  # optional

# like this:
# last_file = glob('../outputs/mega/MEGA*.csv')[-1] # path to file in the folder
# print(last_file[-(len(last_file))+(last_file.rfind('/')+1):])
# MEGA_DF = pd.read_csv(last_file)
# MEGA_DF['date'] = pd.to_datetime(MEGA_DF['date'])
# MEGA_DF.set_index('date', inplace=True)
