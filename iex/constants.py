"""Stores constants."""

import os
from pathlib import Path

from iex import utils

PROJECT_PATH = Path(__file__).resolve().parent.parent
config_path = PROJECT_PATH / "files" / "config.ini"

# credentials
FFX_USERNAME = utils.load_config(config_path, "credentials")["ffx_username"]
FFX_PASSWORD = utils.load_config(config_path, "credentials")["ffx_password"]

# apis
IEX_API_LIVE = os.getenv("IEX_API_LIVE")
IEX_API_SANDBOX = os.getenv("IEX_API_SANDBOX")
FRED_API = utils.load_config(config_path, "api")["fred_api"]

# other
if os.path.isfile(r"/app/files/transactions.xlsx"):
    REDIS_URL = utils.load_config(config_path, "other")["redis_url"]
else:
    # if debugging locally will need a redis
    REDIS_URL = utils.load_config(config_path, "other")["local_redis"]
