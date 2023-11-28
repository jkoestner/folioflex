"""
Market Screeners.

Provides market screeners
"""

import logging

from folioflex.utils import config_helper

# logging options https://docs.python.org/3/library/logging.html
logger = logging.getLogger(__name__)
logger.setLevel(config_helper.LOG_LEVEL)
if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

# provides the logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
