"""Tests the utilities."""

from datetime import datetime

from iex import constants, utils
from iex.dashboard import dashboard_helper

config_path = constants.ROOT_PATH / "tests" / "files" / "test_portfolio.ini"
config = utils.load_config(config_path, "test")


def test_config_load():
    """Checks if config loads correctly."""
    assert (
        config["tx_file"] == "tests/files/test_transactions.csv"
    ), "File did not match."
    assert config["filter_type"] == ["Dividend"], "Filters did not match."
    assert config["funds"] == ["BLKRK"], "Funds did not match."
    assert config["delisted"] == [
        "CCIV",
        "AQUA",
    ], "Delisted did not match"
    assert config["benchmarks"] == ["IVV"], "Benchmarks did not match."


def test_datetime_to_unix():
    """Checks if datetime to unix milliseconds works."""
    unix = dashboard_helper.unix_time_millis(datetime(2022, 6, 17, 0, 0))

    assert unix == 1655424000, "Unix conversion not matching."
