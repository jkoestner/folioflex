"""Tests the portfolio tracker."""

import pathlib
import pandas as pd
from pyxirr import xirr

try:
    import portfolio
except (ImportError, ModuleNotFoundError):
    from iex.util import portfolio

PROJECT_PATH = pathlib.Path(__file__).resolve().parent.parent

tx_file = PROJECT_PATH / pathlib.Path("tests") / "files" / "test_transactions.xlsx"

filter_type = ["Dividend"]
funds = ["BLKRK"]
delisted = ["CCIV"]
other_fields = ["broker"]
date = "05-02-2022"

pf = portfolio.Portfolio(
    tx_file,
    filter_type=filter_type,
    funds=funds,
    delisted=delisted,
    other_fields=other_fields,
)


def test_portfolio_load():
    """Checks if portfolio class can connect."""
    assert pf.file is not None, "Expected that portfolio connects."


def test_transactions_load():
    """Checks if transactions load correctly."""
    assert len(pf.transactions) == len(
        pd.read_excel(tx_file)
    ), "Expected to have no differences in loading file."


def test_calc_cumulative_units():
    """Checks calculations of performance - cumulative units."""
    performance = pf.get_performance(date=date)
    test_df = pd.read_excel(tx_file)
    test_sum = test_df[test_df["ticker"] == "AMD"]["units"].sum()

    assert (
        performance.loc["AMD", "cumulative_units"] == test_sum
    ), "Expected cumulative_units to be sum of units"


def test_calc_average_price():
    """Checks calculations of performance - average price."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["AMD", "average_price"], 2) == 99.25
    ), "Expected average price to match the weighted cost basis"


def test_calc_return_pct():
    """Checks calculations of performance - return percent."""
    performance = pf.get_performance(date=date)

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
    return_pct

    assert round(performance.loc["AMD", "return_pct"], 4) == round(
        return_pct, 4
    ), "Expected return percentage to match dollar weight"


def test_calc_market_value():
    """Checks calculations of performance - market value."""
    performance = pf.get_performance(date=date)
    performance["test_market_value"] = (
        performance["last_price"] * performance["cumulative_units"]
    )
    performance.loc["portfolio", "test_market_value"] = performance[
        "test_market_value"
    ].sum()

    assert (
        performance.loc["portfolio", "market_value"]
        == performance.loc["portfolio", "test_market_value"]
    ), "Expected market_value to be last_price * cumulative_units"


def test_calc_cumulative_cost():
    """Checks calculations of performance - cumulative cost."""
    performance = pf.get_performance(date=date)
    test_df = pd.read_excel(tx_file)
    test_cost = (
        test_df[(test_df["ticker"] == "Cash") & (test_df["date"] <= date)]["cost"].sum()
    ) * -1

    assert (
        performance.loc["portfolio", "cumulative_cost"] == test_cost
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


def test_calc_unrealized_return():
    """Checks calculations of performance - unrealized return."""
    performance = pf.get_performance(date=date)
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
    performance["test_realized"] = performance["return"] - performance["unrealized"]

    assert round(performance.loc["portfolio", "realized"], 2) == round(
        performance.loc["portfolio", "test_realized"], 2
    ), "Expected realized to be return - unrealized"


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
