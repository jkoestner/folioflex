"""Module for handling assets."""

import pandas as pd
import sqlalchemy as sa

from folioflex.portfolio import wrappers
from folioflex.utils import config_helper, custom_logger, database

pd.options.display.float_format = "{:,.2f}".format

logger = custom_logger.setup_logging(__name__)


def get_asset_value(config_path, asset=None, asset_group=None, db_write=False):
    """
    Get the value of asset/s.

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

    Returns
    -------
    asset_df : DataFrame
        A DataFrame with the asset values

    """
    # initialize variabls
    items = []
    rows = []
    sections = list(config_helper.get_config_options(config_path, "assets").keys())

    # get list of items
    if asset is None and asset_group is None:
        for section in sections:
            items += list(
                config_helper.get_config_options(config_path, "assets", section).keys()
            )
    elif asset is not None and asset_group is None:
        items.append(asset)
    elif asset is None and asset_group is not None:
        items = list(
            config_helper.get_config_options(config_path, "assets", asset_group).keys()
        )
    else:
        logger.error("Please provide either an asset or an asset group.")
        return
    logger.info(f"Getting the value of assets: {', '.join(items)}")

    # get the value of assets
    for item in items:
        for section in sections:
            if item in config_helper.get_config_options(config_path, "assets", section):
                asset_group = section
        if asset_group == "cars":
            params = config_helper.get_config_options(
                config_path, "assets", "cars", item
            )
            value = wrappers.KBB().get_value(params)
            rows.append(
                {
                    "date": pd.Timestamp.now().date(),
                    "asset": item,
                    "value": value,
                    "params": params,
                }
            )

        elif asset_group == "houses":
            pass
        else:
            logger.error(f"Asset group '{asset_group}' not found.")
            return

    asset_df = pd.DataFrame(rows)
    if db_write:
        engine = database.Engine(config_path)
        engine.write_table(
            table_name="ffx_assets", df=asset_df, dtype={"params": sa.types.JSON}
        )

    return asset_df


def create_asset_table(engine):
    """
    Create a table of assets from the data source.

    Parameters
    ----------
    engine : SQLAlchemy engine
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
    ]
    engine.create_table(table_name, columns)
