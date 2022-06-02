"""Tests the portfolio tracker."""

import pathlib

import pandas as pd

try:
    import testing
except (ImportError, ModuleNotFoundError):
    from iex.util import testing

PROJECT_PATH = pathlib.Path(__file__).resolve().parent.parent

tx_file = PROJECT_PATH / pathlib.Path("tests") / "files" / "transactions.xlsx"


def test_portfolio_load():
    """Checks if portfolio class can connect."""
    pf = testing.portfolio(tx_file, filter_type=["Cash", "Dividend"])

    assert pf.file is not None, "Expected that portfolio connects."


def test_transactions_load():
    """Checks if transactions load correctly."""
    pf = testing.portfolio(tx_file, filter_type=["Cash", "Dividend"])

    assert len(pf.transactions) == len(
        pd.read_excel(tx_file)
    ), "Expected to have no differences in loading file."


def test_perfomance_calculations():
    """Checks calculations of performance."""
    pf = testing.portfolio(tx_file, filter_type=["Cash", "Dividend"], funds=["BLKRK"])
    performance = pf.get_performance(date="05-02-2022")

    assert (
        performance.loc["AMD", "cumulative_units"] == 16
    ), "Expected cumulative_units to be sum of units"

    assert (
        round(performance.loc["AMD", "average_price"], 2) == 99.25
    ), "Expected average price to match the weighted cost basis"

    assert (
        round(performance.loc["AMD", "return_pct"], 4) == -0.0013
    ), "Expected return percentage to match dollar weight"

    assert (
        round(performance.loc["portfolio", "market_value"], 0) == 15854
    ), "Expected market_value to be last_price * cumulative_units"

    assert (
        round(performance.loc["portfolio", "cumulative_cost"], 0) == 21433
    ), "Expected cumulative_cost to be sum of cost"

    assert (
        round(performance.loc["portfolio", "return"], 0) == -5580
    ), "Expected return to be market_value - cumulative_cost"

    assert (
        round(performance.loc["portfolio", "unrealized"], 0) == -5728
    ), "Expected unrealized to be market_value - average_price * cumulative units"

    assert (
        round(performance.loc["portfolio", "realized"], 0) == 149
    ), "Expected realized to be return - unrealized"
