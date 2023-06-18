"""Stores pages constants."""

from iex.util import utils
from iex.portfolio import portfolio

# tracker vars
tracker_tx_file = utils.constants.remote_path + r"transactions.xlsx"
tracker_portfolio = portfolio.Portfolio(
    tracker_tx_file,
    filter_type=["Dividend"],
    funds=["BLKRK"],
    benchmarks=["IVV"],
)
