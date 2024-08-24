"""
Helpers.

There are a number of functions that are used across the portfolio
module.

"""

from datetime import date, datetime, timedelta

import pandas as pd
import pandas_market_calendars as mcal
from dateutil.parser import parse

from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


def check_stock_dates(tx_df, fix=False, warning=True, timezone="local"):
    """
    Check that the transaction dates are valid.

    This function checks that the transaction dates are valid stock market
    dates. If the dates are not valid, then the dates will be fixed to the
    previous valid date.

    Note:
        Currently using date as the check, but may move to datetime,
        and therefore leaving in timezone.

    Parameters
    ----------
    tx_df : DataFrame (with date column), str, or date
        transactions dataframe
    fix : bool (optional)
        if True then the dates will be fixed to previous valid date
    warning : bool (optional)
        if True then a warning will be logged if dates are fixed
    timezone : str (optional)
        timezone to use for checking dates

    Returns
    -------
    dict
        A dictionary containing:
            invalid_dt : list
                list of dates that are not valid
            fix_tx_df : DataFrame
                transactions dataframe with fixed dates if fix=True

    """
    if not isinstance(tx_df, pd.DataFrame) and not isinstance(tx_df, (str, date)):
        raise ValueError(
            f"tx_df must be a pandas DataFrame, str, or date and not `{type(tx_df)}`)"
        )

    if isinstance(tx_df, (str, date)):
        logger.debug("Checking a single string or date")
        tx_df = pd.DataFrame({"date": [pd.to_datetime(tx_df)]})

    # Check if dates are valid
    if not isinstance(tx_df["date"].iloc[0], date) and not isinstance(
        tx_df["date"].iloc[0], datetime
    ):
        logger.warning(
            "The date column is not a date object, please convert it to a date object"
        )

    # get the timezone
    if timezone == "local":
        timezone = config_helper.LOCAL_TIMEZONE

    # date checks
    tx_df_min = tx_df["date"].min() - timedelta(days=7)
    tx_df_max = tx_df["date"].max()
    stock_dates = mcal.get_calendar("NYSE").schedule(
        start_date=tx_df_min, end_date=tx_df_max
    )
    stock_dates["market_open"] = convert_date_to_timezone(
        stock_dates["market_open"], timezone
    )
    stock_dates["market_close"] = convert_date_to_timezone(
        stock_dates["market_close"], timezone
    )
    stock_dates = pd.to_datetime(stock_dates["market_open"]).dt.date

    # change datetime to date
    if isinstance(tx_df["date"].iloc[0], datetime):
        tx_df["date"] = pd.to_datetime(tx_df["date"]).dt.date
    fix_tx_df = tx_df.copy()

    # Get dates which are not within market hours
    invalid_dt = fix_tx_df["date"][~fix_tx_df["date"].isin(stock_dates)]
    invalid_dt_unique = list(invalid_dt.unique())

    if fix and len(invalid_dt_unique) > 0:
        fix_dt_unique = []
        for i in invalid_dt_unique:
            fix_dt = stock_dates[stock_dates < i].iloc[-1]
            fix_dt_unique.append(fix_dt)
            fix_tx_df.loc[fix_tx_df["date"] == i, "date"] = fix_dt
        if warning:
            logger.warning(
                f"{len(invalid_dt)} transaction(s) dates were fixed to previous "
                f"valid date such as {invalid_dt_unique[0]} updated "
                f"to {fix_dt_unique[0]} \n"
            )

    # Checking that dates were fixed
    invalid_dt = fix_tx_df["date"][~fix_tx_df["date"].isin(stock_dates)].to_list()
    invalid_dt = [datetime.strftime(i, "%Y-%m-%d") for i in invalid_dt]
    if len(invalid_dt) > 0:
        logger.warning(
            f"{len(invalid_dt)} transaction(s) dates were done outside of stock market "
            f"dates such as {invalid_dt[0]} \n"
        )
    return {"invalid_dt": invalid_dt, "fix_tx_df": fix_tx_df}


def convert_date_to_timezone(date_series, timezone="local"):
    """
    Convert date column to a specific timezone.

    Parameters
    ----------
    date_series : series
        series with date column
    timezone : str (optional)
        timezone to convert the date to

    Returns
    -------
    converted_date : series
        series with date column converted to timezone

    """
    if not isinstance(date_series, pd.Series):
        raise ValueError("date_series must be a pandas Series")

    if timezone == "local":
        timezone = config_helper.LOCAL_TIMEZONE
    elif timezone is None and date_series.dt.tz:
        converted_date = pd.to_datetime(date_series).dt.tz_localize(timezone)
    elif date_series.dt.tz:
        converted_date = pd.to_datetime(date_series).dt.tz_convert(timezone)
    else:
        converted_date = pd.to_datetime(date_series).dt.tz_localize(timezone)
    return converted_date


def most_recent_stock_date():
    """Get the most recent stock date."""
    stock_dates = mcal.get_calendar("NYSE").schedule(
        start_date=date.today() - timedelta(days=7), end_date=date.today()
    )
    return stock_dates["market_open"].max().date()


def prettify_dataframe(dataframe):
    """
    Prettify a dataframe with formatting.

    Changes columns with pct to have percentage formatting.

    Parameters
    ----------
    dataframe : DataFrame
        dataframe to prettify

    Returns
    -------
    DataFrame
        prettified dataframe

    """
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("dataframe must be a pandas DataFrame")

    pct_cols = dataframe.filter(like="pct").columns
    for pct_col in pct_cols:
        dataframe[pct_col] = dataframe[pct_col].apply(
            lambda x: "{:.2%}".format(x) if x is not None else "NaN"
        )

    return dataframe


def convert_lookback(lookback):
    """
    Convert lookback to an integer.

    Parameters
    ----------
    lookback : str, int, or date
        lookback to convert

    Returns
    -------
    converted_lookback : int
        converted lookback

    """

    def is_string_a_date(string):
        try:
            parse(string)
            return True
        except ValueError:
            return False

    def is_string_a_number(string):
        return string.isdigit()

    if isinstance(lookback, str):
        if is_string_a_date(lookback):
            converted_lookback = (date.today() - pd.to_datetime(lookback).date()).days
        elif is_string_a_number(lookback):
            converted_lookback = int(lookback)
        elif lookback == "ytd":
            converted_lookback = (date.today() - date(date.today().year, 1, 1)).days
        else:
            raise ValueError(
                f"lookback string must be a date, number, or ytd and not `{lookback}`"
            )
    elif isinstance(lookback, int):
        converted_lookback = lookback
    elif isinstance(lookback, date):
        converted_lookback = (date.today() - lookback).days
    else:
        raise ValueError(
            f"lookback must be a string, int, or date and not {type(lookback)}"
        )
    return converted_lookback
