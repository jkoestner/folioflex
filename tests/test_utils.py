"""Tests the utilities."""

from datetime import datetime

from folioflex.dashboard.utils import dashboard_helper
from folioflex.utils import config_helper

config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_portfolio.ini"
config_dict = config_helper.get_config_options(config_path, "test")


def test_config_load():
    """Checks if config loads correctly."""
    assert (
        config_dict["tx_file"] == "tests/files/test_transactions.csv"
    ), "File did not match."
    assert config_dict["filter_type"] == [], "Filters did not match."
    assert config_dict["funds"] == ["BLKRK"], "Funds did not match."
    assert config_dict["delisted"] == [
        "CCIV",
        "AQUA",
    ], "Delisted did not match"
    assert config_dict["benchmarks"] == ["IVV"], "Benchmarks did not match."


def test_datetime_to_unix():
    """Checks if datetime to unix milliseconds works."""
    unix = dashboard_helper.unix_time_millis(datetime(2022, 6, 17, 0, 0))

    assert unix == 1655424000, "Unix conversion not matching."
