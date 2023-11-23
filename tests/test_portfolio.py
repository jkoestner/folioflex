"""Tests the portfolio tracker."""
from datetime import timedelta

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from pyxirr import xirr

from folioflex.portfolio import portfolio
from folioflex.utils import config_helper

date = "05-02-2022"  # date to test for performance
config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_portfolio.ini"

pf = portfolio.Portfolio(config_path=config_path, portfolio="test")
config_dict = config_helper.get_config_options(config_path, "test")


def test_portfolio_load():
    """Checks if portfolio class can connect."""
    assert pf.file is not None, "Expected that portfolio connects."


def test_transactions_load():
    """Checks if transactions load correctly."""
    assert len(pf.transactions) == len(
        pd.read_csv(pf.file, parse_dates=["date"])
    ), "Expected to have no differences in loading file."


def test_calc_cumulative_units():
    """Checks calculations of performance - cumulative units."""
    performance = pf.get_performance(date=date)
    test_df = pd.read_csv(pf.file, parse_dates=["date"])
    test_sum = test_df[test_df["ticker"] == "AMD"]["units"].sum()

    assert (
        performance.loc["AMD", "cumulative_units"] == test_sum
    ), "Expected cumulative_units to be sum of units"


def test_calc_price():
    """Checks calculations of performance - sale price."""
    transactions = pf.transactions_history
    transactions = transactions[
        (transactions["units"] != 0)
        & (transactions["units"].notnull())
        & (~transactions["ticker"].str.contains("benchmark"))
        & (~transactions["ticker"].str.contains("Cash"))
        & (~transactions["ticker"].str.contains("NVDA"))  # don't include stock splits
    ]
    price = transactions["price"].sum()

    test_df = pd.read_csv(pf.file, parse_dates=["date"])
    test_df = test_df[
        (~test_df["ticker"].str.contains("Cash"))
        & (~test_df["ticker"].str.contains("NVDA"))
        & (~test_df["type"].str.contains("DIVIDEND"))
    ]
    test_price = test_df["price"].sum()

    assert round(price, 2) == round(
        test_price, 2
    ), "Expected sale price to match transaction file"


def test_calc_average_price():
    """Checks calculations of performance - average price."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["AMD", "average_price"], 2) == 99.25
    ), "Expected average price to match the weighted cost basis"


def test_calc_return_pct():
    """Checks calculations of performance - return percent."""
    performance = pf.get_performance(date=date, prettify=False)

    current_price = pf.transactions_history[
        (pf.transactions_history["ticker"] == "AMD")
        & (pf.transactions_history["date"] == date)
    ]
    ticker_transactions = pf.transactions[(pf.transactions["ticker"] == "AMD")].copy()
    ticker_transactions["market_value"] = ticker_transactions["cost"]
    ticker_transactions = pd.concat(
        [ticker_transactions, current_price], ignore_index=True
    )
    return_pct = xirr(ticker_transactions["date"], ticker_transactions["market_value"])

    assert round(performance.loc["AMD", "dwrr_ann_pct"], 4) == round(
        return_pct, 4
    ), "Expected return percentage to match dollar weight"


def test_calc_div_return_pct():
    """Checks calculations of performance - return percent."""
    performance = pf.get_performance(date=date, prettify=False)

    assert (
        round(performance.loc["SPY", "div_dwrr_pct"], 2) == 0.10
    ), "Expected dividend return percentage to match dollar weight"


def test_calc_market_value():
    """Checks calculations of performance - market value."""
    performance = pf.get_performance(date=date)
    performance = performance[~performance.index.str.contains("benchmark")].copy()
    performance["test_market_value"] = (
        performance["last_price"] * performance["cumulative_units"]
    )
    performance.loc["portfolio", "test_market_value"] = performance[
        "test_market_value"
    ].sum()

    assert round(performance.loc["portfolio", "market_value"], 2) == round(
        performance.loc["portfolio", "test_market_value"], 2
    ), "Expected market_value to be last_price * cumulative_units"


def test_calc_cumulative_cost():
    """Checks calculations of performance - cumulative cost."""
    performance = pf.get_performance(date=date)
    test_df = pd.read_csv(pf.file, parse_dates=["date"])
    test_cost = (
        test_df[(test_df["ticker"] == "Cash") & (test_df["date"] <= date)]["cost"].sum()
    ) * -1

    assert round(performance.loc["portfolio", "cumulative_cost"], 2) == round(
        test_cost, 2
    ), "Expected cumulative_cost to be sum of cost"


def test_calc_return():
    """Checks calculations of performance - return."""
    performance = pf.get_performance(date=date)
    performance["test_return"] = (
        performance["market_value"] + performance["cumulative_cost"]
    )

    assert round(performance.loc["portfolio", "return"], 2) == round(
        performance.loc["portfolio", "test_return"], 2
    ), "Expected return to be market_value - cumulative_cost"


def test_calc_cash_return():
    """Checks calculations of performance - return."""
    cash_return = pf._get_return_pct("Cash", "9/21/2023", lookback=365)[
        "dwrr_return_pct"
    ]
    cash_div_return = pf._get_return_pct("Cash", "9/21/2023", lookback=365)[
        "div_dwrr_return_pct"
    ]

    assert round(cash_return, 2) == 0.10, "Expected cash return to be 10%"
    assert round(cash_div_return, 2) == 0.00, "Expected cash div return to be 0%"


def test_calc_dividend():
    """Checks calculations of performance - dividend."""
    performance = pf.get_performance(date=date)
    test_df = pd.read_csv(pf.file, parse_dates=["date"])
    test_dividend = test_df[
        (test_df["type"] == "DIVIDEND") & (test_df["date"] <= date)
    ]["cost"].sum()

    assert round(performance.loc["portfolio", "cumulative_dividend"], 2) == round(
        test_dividend, 2
    ), "Expected dividend to be sum of dividend transactions"


def test_calc_unrealized_return():
    """Checks calculations of performance - unrealized return."""
    performance = pf.get_performance(date=date)
    performance = performance[~performance.index.str.contains("benchmark")].copy()
    performance["test_unrealized"] = (
        performance["market_value"]
        - performance["average_price"] * performance["cumulative_units"]
    )
    performance.loc["portfolio", "test_unrealized"] = performance[
        "test_unrealized"
    ].sum()

    assert round(performance.loc["portfolio", "unrealized"], 2) == round(
        performance.loc["portfolio", "test_unrealized"], 2
    ), "Expected unrealized to be market_value - average_price * cumulative units"


def test_calc_realized_return():
    """Checks calculations of performance - realized return."""
    performance = pf.get_performance(date=date)
    performance["test_realized"] = (
        performance["return"]
        - performance["unrealized"]
        - performance["cumulative_dividend"]
    )

    assert round(performance.loc["portfolio", "realized"], 2) == round(
        performance.loc["portfolio", "test_realized"], 2
    ), "Expected realized to be return - unrealized"


def test_lookback():
    """Checks calculations of fund transactions."""
    lookback = 10
    ticker = "AMD"
    performance = pf.get_performance(date=date, lookback=lookback)

    test_tx_hist_df = pf.transactions_history.copy()
    ticker_df = test_tx_hist_df[test_tx_hist_df["ticker"] == ticker]
    ticker_df = ticker_df[ticker_df["date"] <= date]
    cal_start_date = ticker_df["date"].max() - timedelta(days=lookback)
    buffer_date = cal_start_date - timedelta(days=7)
    stock_dates = (
        mcal.get_calendar("NYSE").schedule(start_date=buffer_date, end_date=date).index
    )
    start_date = max([date for date in stock_dates if date <= cal_start_date])
    ticker_df = ticker_df[ticker_df["date"] >= start_date]

    # get the entry price, transactions, current price
    entry_price = ticker_df[ticker_df["date"] == ticker_df["date"].min()].copy()
    ticker_transactions = ticker_df[
        (ticker_df["date"] > ticker_df["date"].min())
        & (ticker_df["date"] <= date)
        & ((ticker_df["cost"] != 0) | (ticker_df["dividend"] != 0))
    ].copy()
    current_price = ticker_df[(ticker_df["date"] == date)].copy()

    # equity + dividend
    entry_price["return_txs"] = np.where(
        entry_price["units"] == entry_price["cumulative_units"],
        entry_price["cumulative_cost"],
        -entry_price["market_value"],
    )
    ticker_transactions["return_txs"] = ticker_transactions["cost"]
    current_price["return_txs"] = (
        current_price["market_value"] + current_price["cumulative_dividend"]
    )

    # combine the transactions
    return_transactions = pd.concat(
        [entry_price, ticker_transactions, current_price], ignore_index=True
    ).sort_values(by="date", ascending=False)
    return_transactions["return_txs"] = return_transactions["return_txs"].replace(
        np.nan, 0
    )

    # get return pcts
    start_date = return_transactions["date"].iloc[-1]
    end_date = return_transactions["date"].iloc[0]
    days = (end_date - start_date).days
    dwrr_ann_return_pct = xirr(
        return_transactions["date"], return_transactions["return_txs"]
    )
    test_dwrr_pct = (1 + dwrr_ann_return_pct) ** (days / 365) - 1
    amd_dwrr_pct = float(performance.at["AMD", "dwrr_pct"].strip("%")) / 100

    test_return = return_transactions["return_txs"].sum()
    amd_return = performance.at["AMD", "return"]

    assert round(amd_dwrr_pct, 2) == round(
        test_dwrr_pct, 2
    ), "Expected return pct for AMD to match the test return pct"

    assert round(amd_return, 2) == round(
        test_return, 2
    ), "Expected return for AMD to match the test return"


def test_fund_trans():
    """Checks calculations of fund transactions."""
    performance = pf.get_performance(date="05-27-2022")
    test_units = pf.transactions[pf.transactions["ticker"] == "BLKRK"]["units"].sum()
    performance["test_market_value"] = (
        performance["last_price"] * performance["cumulative_units"]
    )

    assert (
        performance.loc["BLKRK", "cumulative_units"] == test_units
    ), "Expected cumulative_units to be sum of units"

    assert (
        performance.loc["BLKRK", "average_price"] == 12
    ), "Expected average price to match the weighted cost basis"

    assert (
        performance.loc["BLKRK", "market_value"]
        == performance.loc["BLKRK", "test_market_value"]
    ), "Expected market_value to be last_price * cumulative_units"


def test_delisted_trans():
    """Checks calculations of delisted transactions."""
    performance = pf.get_performance(date="05-27-2022")
    performance["test_return"] = (
        performance["market_value"] + performance["cumulative_cost"]
    )

    assert (
        performance.loc["CCIV", "return"] == performance.loc["CCIV", "test_return"]
    ), "Expected cumulative_units to be market_value - cumulative_cost"


def test_benchmark():
    """Checks benchmark is calculating market value correctly."""
    performance = pf.get_performance(date=date)
    cash_tx = pf.transactions[pf.transactions["ticker"] == "Cash"].copy()
    cash_tx = cash_tx[cash_tx["date"] <= date]
    cash_tx["ticker"] = config_dict["benchmarks"][0]

    price_history = pf.price_history

    cash_tx_hist = (
        pd.merge(
            price_history,
            cash_tx[["date", "ticker", "price", "units", "cost"]],
            how="outer",
            on=["date", "ticker"],
        )
        .fillna(0)
        .sort_values(by=["ticker", "date"], ignore_index=True)
    )
    cash_tx_hist = cash_tx_hist[cash_tx_hist["ticker"] == config_dict["benchmarks"][0]]
    cash_tx_hist["price"] = np.where(
        cash_tx_hist["units"] == 0,
        0,
        cash_tx_hist["last_price"],
    )
    cash_tx_hist["units"] = np.where(
        cash_tx_hist["units"] == 0,
        0,
        cash_tx_hist["cost"] / cash_tx_hist["price"],
    )

    benchmark_market_value = (
        cash_tx_hist["units"].sum()
        * cash_tx_hist[cash_tx_hist["date"] == date]["last_price"].values[0]
    )

    assert round(performance.loc["benchmark-IVV", "market_value"], 2) == round(
        benchmark_market_value, 2
    ), "Expected benchmark to be based on cash transactions"


def test_yf_download():
    """Checks that yf is downloading the same data."""
    test_price_history = pd.read_csv(
        config_dict["history_offline"], index_col=0, parse_dates=["date"]
    )
    price_history = pf.price_history
    price_history = price_history[price_history["date"] <= "10/27/2023"]
    assert test_price_history.equals(
        price_history
    ), "Expected the downloaded price history to match the offline file."
