"""Stores constants."""

import os
from rq import Queue

from iex.util import utils, portfolio, worker

alpha_vantage_api = os.environ["ALPHAVANTAGE_API"]
iex_api_live = os.environ["IEX_API_LIVE"]
iex_api_sandbox = os.environ["IEX_API_SANDBOX"]
aws_tx_file = os.environ["AWS_TX_FILE"]
remote_path = utils.get_remote_path()

# tracker vars
tracker_tx_file = remote_path + r"transactions.xlsx"
tracker_portfolio = portfolio.portfolio(
    tracker_tx_file, filter_type=["Cash", "Dividend"], funds=["BLKRK"]
)

# personal vars
q = Queue(connection=worker.conn)
personal_tx_file = aws_tx_file
# personal_portfolio = q.enqueue(worker.portfolio_query, personal_tx_file)
