"""Stores constants."""

import os

from iex import utils

ROOT_PATH = utils.ROOT_PATH
CONFIG_PATH = utils.CONFIG_PATH
TESTS_PATH = utils.TESTS_PATH
config_file = CONFIG_PATH / "config.ini"

# credentials
FFX_USERNAME = utils.load_config(config_file, "credentials")["ffx_username"]
FFX_PASSWORD = utils.load_config(config_file, "credentials")["ffx_password"]

# apis
FRED_API = utils.load_config(config_file, "api")["fred_api"]

# other
if os.path.exists(r"/app/tests"):
    REDIS_URL = utils.load_config(config_file, "other")["redis_url"]
else:
    # if debugging locally will need a redis
    REDIS_URL = utils.load_config(config_file, "other")["local_redis"]
