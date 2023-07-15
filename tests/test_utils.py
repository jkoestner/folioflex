"""Tests the utilities."""

from datetime import datetime

try:
    import utils
except (ImportError, ModuleNotFoundError):
    from iex.dashboard import utils


def test_datetime_to_unix():
    """Checks if datetime to unix milliseconds works."""
    unix = utils.unix_time_millis(datetime(2022, 6, 17, 0, 0))

    assert unix == 1655424000, "Unix conversion not matching."
