"""Stores constants."""

import os

from iex.util import utils

alpha_vantage_api = os.environ["ALPHAVANTAGE_API"]
iex_api_live = os.environ["IEX_API_LIVE"]
iex_api_sandbox = os.environ["IEX_API_SANDBOX"]
remote_path = utils.get_remote_path()
