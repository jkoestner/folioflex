"""Database helper functions for folioflex."""

import pandas as pd
import sqlalchemy as sa

from folioflex.utils import config_helper, custom_logger

pd.options.display.float_format = "{:,.2f}".format

logger = custom_logger.setup_logging(__name__)


class Engine:
    """
    A class to create an engine.

    Parameters
    ----------
    config_path : str
       the location of the config file

    """

    def __init__(self, config_path):
        self.config_path = config_path
        self.engine = self._create_engine()
        self.metadata = sa.MetaData()

    def create_table(self, table_name, columns):
        """
        Create a table in the database.

        Parameters
        ----------
        table_name : str
           The name of the table to create.
        columns : list
            A list of SQLAlchemy Column objects defining the table structure.

         example:
         --------
         table_name = 'ffx_assets'
         columns = [
            Column('date', Date),
            Column('asset', String),
            Column('value', Float),
            Column('params', String)
         ]
         engine.create_table(table_name, columns)

        """
        inspector = sa.inspect(self.engine)
        if not inspector.has_table(table_name):
            table = sa.Table(table_name, self.metadata, *columns)
            try:
                table.create(self.engine)
                logger.info(f"Table '{table_name}' created successfully.")
            except sa.exc.SQLAlchemyError as e:
                logger.error(
                    f"An error occurred while creating table '{table_name}': {e}"
                )
        else:
            logger.info(f"Table '{table_name}' already exists.")

    def drop_table(self, table_name):
        """
        Drop a table from the database.

        Parameters
        ----------
        table_name : str
            The name of the table to drop.

        """
        inspector = sa.inspect(self.engine)
        if inspector.has_table(table_name):
            table = sa.Table(table_name, self.metadata, autoload_with=self.engine)
            try:
                table.drop(self.engine)
                logger.info(f"Table '{table_name}' dropped successfully.")
            except sa.exc.SQLAlchemyError as e:
                logger.error(
                    f"An error occurred while dropping table '{table_name}': {e}"
                )
        else:
            logger.info(f"Table '{table_name}' does not exist.")

    def table_exists(self, table_name):
        """
        Check if a table exists in the database.

        Parameters
        ----------
        table_name : str
            The name of the table to check.

        Returns
        -------
        bool
            True if the table exists, False otherwise.

        """
        inspector = sa.inspect(self.engine)
        return inspector.has_table(table_name)

    def read_table(self, table_name):
        """
        Read a table from the database.

        Parameters
        ----------
        table_name : str
              The name of the table to read.

        Returns
        -------
        DataFrame
              The table as a DataFrame.

        """
        if self.table_exists(table_name):
            return pd.read_sql_table(table_name, self.engine)
        else:
            logger.error(f"Table '{table_name}' does not exist.")
            return pd.DataFrame()

    def write_table(
        self, df, table_name, if_exists="append", avoid_dups=None, **kwargs
    ):
        """
        Write a DataFrame to a table in the database.

        Parameters
        ----------
        df : DataFrame
            The DataFrame to write to the table.
        table_name : str
            The name of the table to write to.
        if_exists : str, default 'replace'
            What to do if the table already exists.
            Options are: 'fail', 'replace', 'append'.
        avoid_dups : list, optional
            A list of columns to check for duplicates before inserting.
        kwargs : dict
            Additional keyword arguments to pass to the DataFrame.to_sql method.


        """
        new_df = df
        if avoid_dups:
            existing_df = pd.read_sql_table(table_name, self.engine)
            existing_df["date"] = existing_df["date"].dt.date
            merged_df = df.merge(
                existing_df[avoid_dups], on=avoid_dups, how="left", indicator=True
            )
            new_df = merged_df[merged_df["_merge"] == "left_only"].drop(
                columns=["_merge"]
            )
        if not new_df.empty:
            new_df.to_sql(
                table_name, self.engine, if_exists=if_exists, index=False, **kwargs
            )
            logger.info(f"Inserted {len(new_df)} new rows into table '{table_name}'.")
        else:
            logger.warning(
                "No new rows to insert; all rows already exist in the table."
            )

    def bulk_update(self, tx_df, table_name, where_column):
        """
        Perform a bulk update on the specified table.

        Parameters
        ----------
        tx_df : DataFrame
            The DataFrame containing the data to update.
        table_name : str
            The name of the table to update.
        where_column : str
            The column to use as the WHERE clause.

        """
        logger.debug(
            f"Updating table '{table_name}' on column '{f'b_{where_column}'}'."
        )
        # get table and valid columns then filter
        table = sa.Table(
            table_name, self.metadata, autoload_with=self.engine, schema="public"
        )
        valid_columns = {c.name for c in table.columns}
        tx_df = tx_df.loc[:, tx_df.columns.isin(valid_columns)]
        bind_where_column = f"bind_{where_column}"
        tx_df = tx_df.rename(columns={where_column: bind_where_column})

        # create the update statement
        update_stmt = table.update().where(
            table.c[where_column] == sa.bindparam(bind_where_column)
        )
        tx_dict = tx_df.to_dict(orient="records")

        # execute the update
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(update_stmt, tx_dict)
                trans.commit()
            except Exception as e:
                trans.rollback()
                raise e

    def _create_engine(self):
        """
        Create an engine.

        Returns
        -------
        engine : SQLAlchemy engine
           The engine to connect to the database.

        """
        # get the database config values
        config_path = self.config_path
        database_dict = config_helper.get_config_options(config_path, "config").get(
            "database", None
        )
        if database_dict is None:
            raise ValueError("Database configuration is missing.")
        db_user = database_dict.get("db_user", None)
        db_pass = database_dict.get("db_pass", None)
        db_host = database_dict.get("db_host", None)
        db_name = database_dict.get("db_name", None)
        db_port = database_dict.get("db_port", None)

        config_values = {
            "db_user": db_user,
            "db_pass": db_pass,
            "db_host": db_host,
            "db_name": db_name,
            "db_port": db_port,
        }
        missing_values = [key for key, value in config_values.items() if value is None]
        if missing_values:
            raise ValueError(
                f"The following configuration values are missing: "
                f"{', '.join(missing_values)}"
            )

        # create the engine
        engine = sa.create_engine(
            f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        )
        logger.info(f"Connected to database: {db_name}")

        return engine
