"""Tests the portfolio tracker."""

import pathlib

import pandas as pd

try:
    import portfolio
except (ImportError, ModuleNotFoundError):
    from iex.util import portfolio

PROJECT_PATH = pathlib.Path(__file__).resolve().parent.parent

tx_file = PROJECT_PATH / pathlib.Path("tests") / "files" / "test_transactions.xlsx"

filter_type = ["Dividend"]
funds = ["BLKRK"]
other_fields = ["broker"]
date = "05-02-2022"
pf = portfolio.Portfolio(
    tx_file, filter_type=filter_type, funds=funds, other_fields=other_fields
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
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        performance.loc["AMD", "cumulative_units"] == 16
    ), "Expected cumulative_units to be sum of units"


def test_calc_average_price():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["AMD", "average_price"], 2) == 99.25
    ), "Expected average price to match the weighted cost basis"


def test_calc_return_pct():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["AMD", "return_pct"], 4) == -0.0013
    ), "Expected return percentage to match dollar weight"


def test_calc_market_value():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["portfolio", "market_value"], 0) == 16420
    ), "Expected market_value to be last_price * cumulative_units"


def test_calc_cumulative_cost():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["portfolio", "cumulative_cost"], 0) == -22003
    ), "Expected cumulative_cost to be sum of cost"


def test_calc_return():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["portfolio", "return"], 0) == -5584
    ), "Expected return to be market_value - cumulative_cost"


def test_calc_unrealized_return():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["portfolio", "unrealized"], 0) == -5732
    ), "Expected unrealized to be market_value - average_price * cumulative units"


def test_calc_realized_return():
    """Checks calculations of performance."""
    performance = pf.get_performance(date=date)

    assert (
        round(performance.loc["portfolio", "realized"], 0) == 149
    ), "Expected realized to be return - unrealized"


def test_fund_index():
    """Checks calculations of fund index."""
    performance = pf.get_performance(date="05-27-2022")

    assert (
        performance.loc["BLKRK", "cumulative_units"] == 10
    ), "Expected cumulative_units to be sum of units"

    assert (
        performance.loc["BLKRK", "average_price"] == 12
    ), "Expected average price to match the weighted cost basis"

    assert (
        performance.loc["BLKRK", "market_value"] == 140
    ), "Expected market_value to be last_price * cumulative_units"
