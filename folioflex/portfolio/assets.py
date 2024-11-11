"""Module for handling assets."""

from typing import TYPE_CHECKING, Optional, Union

import pandas as pd
import plotly.express as px
import sqlalchemy as sa

from folioflex.portfolio import wrappers
from folioflex.utils import config_helper, custom_logger, database

pd.options.display.float_format = "{:,.2f}".format

logger = custom_logger.setup_logging(__name__)

if TYPE_CHECKING:
    import plotly.graph_objects as go


def update_asset_info(
    config_path: str,
    asset: Optional[str] = None,
    asset_group: Optional[str] = None,
    db_write: bool = False,
    proxy: Optional[str] = None,
) -> Union[pd.DataFrame, None]:
    """
    Update the value of asset/s.

    Parameters
    ----------
    config_path : str
        The location of the config file.
    asset : str, optional
        The name of the asset.
    asset_group : str, optional
        The name of the asset group.
    db_write : bool, optional
        Whether to write the data to the database.
    proxy : str, optional
        The proxy to use for the request.

    Returns
    -------
    asset_df : DataFrame
        A DataFrame with the asset values

    """
    # initialize variabls
    items = []
    rows = []
    sections = list(config_helper.get_config_options(config_path, "assets").keys())
    sections.remove("users")

    # get list of items
    if asset is None and asset_group is None:
        for section in sections:
            items += list(
                config_helper.get_config_options(config_path, "assets", section).keys()
            )
    elif asset and asset_group is None:
        items.append(asset)
    elif asset is None and asset_group:
        items = list(
            config_helper.get_config_options(config_path, "assets", asset_group).keys()
        )
    else:
        logger.error("Please provide either an asset or an asset group.")
        return None
    logger.info(f"Getting the value of assets: {', '.join(items)}")

    # process each asset
    for item in items:
        for section in sections:
            if item in config_helper.get_config_options(config_path, "assets", section):
                asset_group = section
                break
        if asset_group == "cars":
            params = config_helper.get_config_options(
                config_path, "assets", "cars", item
            )
            value = wrappers.KBB().get_value(params, proxy=proxy)
        elif asset_group == "houses":
            params = config_helper.get_config_options(
                config_path, "assets", "houses", item
            )
            value = wrappers.Zillow().get_value(params, proxy=proxy)
        else:
            logger.error(f"Asset group '{asset_group}' not found.")
            return None
        rows.append(
            {
                "date": pd.Timestamp.now().date(),
                "asset": item,
                "value": value,
                "params": params,
            }
        )

    asset_df = pd.DataFrame(rows)
    asset_df = asset_df.dropna(subset=["value"])  # drop rows with missing values
    logger.info(f"found {len(asset_df)} assets")
    if db_write:
        engine = database.Engine(config_path)
        engine.write_table(
            table_name="ffx_assets",
            df=asset_df,
            avoid_dups=["date", "asset"],
            dtype={"params": sa.types.JSON},
        )

    return asset_df


def get_asset_df(
    engine: database.Engine,
    current: bool = True,
    user: Optional[str] = None,
    config_path: str = "config.yml",
) -> pd.DataFrame:
    """
    Get the asset df.

    Parameters
    ----------
    engine : ffx engine
        The engine to connect to the database. Used for reading the asset table.
    current : bool, optional
        Whether to get only the most recent value of the asset instead of all values.
    user : str, optional
        The name of the user. Used to only get assets related to the user.
    config_path : str, optional
        The location of the config file. Used if the user is provided.


    Returns
    -------
    asset_df : pd.DataFrame
        A dataframe with the asset info.

    """
    # read in the asset table
    asset_df = engine.read_table("ffx_assets")
    asset_df["date"] = asset_df["date"].dt.date

    # filter by user
    if user:
        user_assets = config_helper.get_config_options(
            config_path, "assets", "users"
        ).get(user, None)
        asset_df = asset_df[asset_df["asset"].isin(user_assets)]

    # add in the checking account
    checking_value = get_checking_value(engine, user=user)
    checking_df = pd.DataFrame(
        {
            "date": [pd.Timestamp.now().date()],
            "asset": ["checking"],
            "value": [checking_value],
        }
    ).dropna(axis=1, how="all")
    asset_df = pd.concat([asset_df, checking_df], ignore_index=True)

    # sort
    asset_df = asset_df[["date", "asset", "value"]]

    # only get the current value of the assets
    if current:
        asset_df = (
            asset_df.sort_values(by="date", ascending=False)
            .groupby("asset")
            .first()
            .reset_index()
        )

    asset_df = asset_df.sort_values(by="date", ascending=False)
    asset_df.loc["total"] = asset_df.select_dtypes("number").sum()

    return asset_df


def get_checking_value(engine: database.Engine, user: Optional[str] = None) -> float:
    """
    Get the value of the checking account.

    Parameters
    ----------
    engine : ffx engine
        The engine to connect to the database.
    user : str, optional
        The name of the user.

    Returns
    -------
    checking_value : float
        The value of the checking account.

    """
    # get the accounts from database
    user_df = engine.read_table("users_table")
    item_df = engine.read_table("items_table")
    account_df = engine.read_table("accounts_table")
    account_df = pd.merge(
        account_df,
        item_df[["id", "plaid_institution_id", "user_id"]],
        left_on="item_id",
        right_on="id",
        how="left",
        suffixes=[None, "_tmp"],
    )
    account_df = pd.merge(
        account_df,
        user_df[["id", "username"]],
        left_on="user_id",
        right_on="id",
        how="left",
        suffixes=[None, "_tmp"],
    )
    if user is not None:
        account_df = account_df[account_df["username"] == user]
    account_df = account_df[account_df["subtype"] == "checking"]
    checking_value = account_df["current_balance"].sum()

    return checking_value


def create_asset_table(engine: database.Engine) -> None:
    """
    Create a table of assets from the data source.

    Parameters
    ----------
    engine : ffx engine
        The engine to connect to the database.

    """
    # the table structure
    table_name = "ffx_assets"
    columns = [
        sa.Column("idx", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date),
        sa.Column("asset", sa.String),
        sa.Column("value", sa.Float),
        sa.Column("params", sa.String),
        sa.UniqueConstraint("date", "asset", name="uix_date_asset"),
    ]
    engine.create_table(table_name, columns)


def display_asset_trend(asset_df: pd.DataFrame) -> "go.Figure":
    """
    Display the asset trend.

    Parameters
    ----------
    asset_df : DataFrame
        The asset DataFrame.

    Returns
    -------
    fig : Figure
        The asset trend figure.

    """
    # create line chart
    fig = px.line(
        asset_df,
        x="date",
        y="value",
        color="asset",
        title="Asset Trend",
        labels={"date": "Date", "value": "Value"},
    )

    return fig
