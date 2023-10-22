"""
Helpers.

There are a number of functions that are used across the portfolio
module.

"""

import logging
import pandas as pd
import pandas_market_calendars as mcal

from datetime import date, datetime, timedelta

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


def check_stock_dates(tx_df, fix=False, timezone="US/Eastern"):
    """Check that the transaction dates are valid.

    Note:
        Currently using date as the check, but may move to datetime,
        and therfore leaving in timezone.

    Parameters
    ----------
    tx_df : DataFrame
        transactions dataframe
    fix : bool (optional)
        if True then the dates will be fixed to previous valid date

    Returns
    -------
    dict
        A dictionary containing:
            invalid_dt : list
                list of dates that are not valid
            fix_tx_df : DataFrame
                transactions dataframe with fixed dates if fix=True

    """
    if isinstance(tx_df, str) or isinstance(tx_df, date):
        logger.info("Checking a single date or string")
        tx_df = pd.DataFrame({"date": [pd.to_datetime(tx_df)]})

    # Check if dates are valid
    if not isinstance(tx_df["date"].iloc[0], date) and not isinstance(
        tx_df["date"].iloc[0], datetime
    ):
        logger.warning(
            "The date column is not a date object, please convert it to a date object"
        )

    # date checks
    tx_df_min = min(tx_df["date"].min(), tx_df["date"].max() - timedelta(days=7))
    tx_df_max = tx_df["date"].max()
    stock_dates = mcal.get_calendar("NYSE").schedule(
        start_date=tx_df_min, end_date=tx_df_max
    )
    stock_dates["market_open"] = stock_dates["market_open"].dt.tz_convert(timezone)
    stock_dates["market_close"] = stock_dates["market_close"].dt.tz_convert(timezone)
    stock_dates = pd.to_datetime(stock_dates["market_open"]).dt.date

    # change datetime to date
    if isinstance(tx_df["date"].iloc[0], datetime):
        tx_df["date"] = pd.to_datetime(tx_df["date"]).dt.date
    fix_tx_df = tx_df.copy()

    # Get dates which are not within market hours
    invalid_dt = fix_tx_df["date"][~fix_tx_df["date"].isin(stock_dates)].to_list()

    if fix and len(invalid_dt) > 0:
        for i in invalid_dt:
            fix_tx_df.loc[tx_df["date"] == i, "date"] = stock_dates[stock_dates < i][-1]
        logger.warning(
            f"{len(invalid_dt)} transaction(s) dates were fixed to previous valid date"
            f" such as {invalid_dt[0]} \n"
        )

    invalid_dt = fix_tx_df["date"][~fix_tx_df["date"].isin(stock_dates)].to_list()
    invalid_dt = [datetime.strftime(i, "%Y-%m-%d") for i in invalid_dt]
    if len(invalid_dt) > 0:
        logger.warning(
            f"{len(invalid_dt)} transaction(s) dates were done outside of stock market "
            f"dates such as {invalid_dt[0]} \n"
        )
    return {"invalid_dt": invalid_dt, "fix_tx_df": fix_tx_df}
