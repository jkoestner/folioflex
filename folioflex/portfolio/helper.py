"""
Helpers.

There are a number of functions that are used across the portfolio
module.

"""

import logging
import pandas_market_calendars as mcal

from datetime import datetime

# logging options https://docs.python.org/3/library/logging.html
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

# provides the logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


def check_stock_dates(tx_df, fix=False):
    """Check that the transaction dates are valid.

    Parameters
    ----------
    tx_df : DataFrame
        transactions dataframe
    fix : bool (optional)
        if True then the dates will be fixed to previous valid date

    """
    # date checks
    tx_df_min = tx_df["date"].min()
    tx_df_max = tx_df["date"].max()
    stock_dates = (
        mcal.get_calendar("NYSE")
        .schedule(start_date=tx_df_min, end_date=tx_df_max)
        .index
    )
    invalid_dt = tx_df["date"][~tx_df["date"].isin(stock_dates)].to_list()

    if fix and len(invalid_dt) > 0:
        for i in invalid_dt:
            tx_df.loc[tx_df["date"] == i, "date"] = stock_dates[stock_dates < i][-1]
        logger.warning(
            f"{len(invalid_dt)} transaction(s) dates were fixed to previous valid date"
        )

    invalid_dt = tx_df["date"][~tx_df["date"].isin(stock_dates)].to_list()
    invalid_dt = [datetime.strftime(i, "%Y-%m-%d") for i in invalid_dt]
    if len(invalid_dt) > 0:
        logger.warning(
            f"{len(invalid_dt)} transaction(s) dates were done outside of stock market "
            f"dates such as {invalid_dt} \n"
        )
    return invalid_dt
