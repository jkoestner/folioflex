"""
Market Screeners.

Provides market screeners
"""

import logging
import logging.config
import os

from folioflex.utils import config_helper

# create logger
logging.config.fileConfig(
    os.path.join(config_helper.CONFIG_PATH, "logging.ini"),
)
logger = logging.getLogger(__name__)
