"""Stores pages constants."""

from iex.util import constants
from iex.portfolio import portfolio

# tracker vars
tracker_tx_file = constants.remote_path + r"transactions.xlsx"
tracker_portfolio = portfolio.Portfolio(
    tracker_tx_file,
    filter_type=["Dividend"],
    funds=["BLKRK"],
    benchmarks=["IVV"],
)