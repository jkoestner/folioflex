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

    def get_user_transactions(self, user_id: int) -> pd.DataFrame:
        """
        Get plaid transactions for a user.

        Parameters
        ----------
        user_id : int
            The id of the user.

        Returns
        -------
        plaid_transactions : pd.DataFrame
            The plaid transactions.

        """
        logger.debug(f"Getting plaid transactions for user `{user_id}`")
        query = """
            SELECT
                t.date,
                t.name,
                t.account_id,
                t.amount,
                t.label,
                t.account_owner,
                t.id
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN items i ON a.item_id = i.id
            WHERE t.user_id = :user_id
                AND t.pending = False
            ORDER BY t.date DESC, t.id DESC
        """

        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query), {"user_id": user_id})
            plaid_transactions = pd.DataFrame(result.fetchall())
            plaid_transactions["date"] = pd.to_datetime(
                plaid_transactions["date"]
            ).dt.strftime("%Y-%m-%d")

        return plaid_transactions

    def get_user_accounts(self, user_id: int) -> pd.DataFrame:
        """
        Get plaid accounts for a user.

        Parameters
        ----------
        user_id : int
            The id of the user.

        Returns
        -------
        plaid_accounts : pd.DataFrame
            The plaid accounts.

        """
        logger.debug(f"Getting plaid accounts for user `{user_id}`")
        query = """
            SELECT
                a.item_id,
                a.id,
                a.official_name,
                a.current_balance,
                a.type,
                a.updated_at
            FROM accounts a
            JOIN items i ON a.item_id = i.id
            WHERE a.user_id = :user_id
            ORDER BY a.updated_at DESC, a.id DESC
        """

        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query), {"user_id": user_id})
            plaid_accounts = pd.DataFrame(result.fetchall())
            plaid_accounts["updated_at"] = pd.to_datetime(
                plaid_accounts["updated_at"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

        return plaid_accounts

    def get_user_id(self, username: str) -> int:
        """
        Get the user id for a username.

        Parameters
        ----------
        username : str
            The username.

        Returns
        -------
        user_id : int
            The user id.

        """
        query = "SELECT id FROM users WHERE username = :username"
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query), {"username": username})
            user_id = result.fetchone()[0]
        return user_id

    def get_item_info(self, plaid_item_id: str) -> dict:
        """
        Get information about an item.

        Parameters
        ----------
        plaid_item_id : str
            The plaid item id.

        Returns
        -------
        item : dict
            The item for the plaid item id.

        """
        logger.debug(f"Getting plaid item for plaid_item_id `{plaid_item_id}`")
        query = "SELECT * FROM items WHERE plaid_item_id = :plaid_item_id"
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query), {"plaid_item_id": plaid_item_id})
            item = dict(result.mappings().fetchone())
        return item

    def add_transactions(self, transactions: list) -> None:
        """
        Add or update transactions in the database.

        Parameters
        ----------
        transactions : list
            List of transactions

        """
        query = """
            INSERT INTO transactions_table
                (
                    account_id,
                    plaid_transaction_id,
                    plaid_category_id,
                    category,
                    subcategory,
                    type,
                    name,
                    amount,
                    iso_currency_code,
                    unofficial_currency_code,
                    date,
                    pending,
                    primary_category,
                    detailed_category,
                    confidence_level,
                    account_owner
                )
            VALUES
                (
                    :account_id,
                    :plaid_transaction_id,
                    :plaid_category_id,
                    :category,
                    :subcategory,
                    :type,
                    :name,
                    :amount,
                    :iso_currency_code,
                    :unofficial_currency_code,
                    :date,
                    :pending,
                    :primary_category,
                    :detailed_category,
                    :confidence_level,
                    :account_owner
                )
            ON CONFLICT (plaid_transaction_id) DO UPDATE SET
                plaid_category_id = EXCLUDED.plaid_category_id,
                category = EXCLUDED.category,
                subcategory = EXCLUDED.subcategory,
                type = EXCLUDED.type,
                name = EXCLUDED.name,
                amount = EXCLUDED.amount,
                iso_currency_code = EXCLUDED.iso_currency_code,
                unofficial_currency_code = EXCLUDED.unofficial_currency_code,
                date = EXCLUDED.date,
                pending = EXCLUDED.pending,
                primary_category = EXCLUDED.primary_category,
                detailed_category = EXCLUDED.detailed_category,
                confidence_level = EXCLUDED.confidence_level,
                account_owner = EXCLUDED.account_owner
        """
        try:
            with self.engine.connect() as conn:
                try:
                    conn.execute(sa.text(query), transactions)
                    conn.commit()
                except sa.exc.SQLAlchemyError as e:
                    conn.rollback()
                    logger.error(f"Error executing transaction query: {e!s}")
                    raise
        except Exception as e:
            logger.error(f"Unexpected error in add_transactions: {e!s}")
            raise

    def delete_transactions(self, plaid_transaction_ids: list) -> None:
        """
        Delete transactions from the database.

        Parameters
        ----------
        plaid_transaction_ids : list
            List of plaid transaction ids.

        """
        query = "DELETE FROM transactions_table WHERE plaid_transaction_id = ANY(:plaid_transaction_ids)"
        with self.engine.connect() as conn:
            try:
                conn.execute(
                    sa.text(query), {"plaid_transaction_ids": plaid_transaction_ids}
                )
                conn.commit()
            except sa.exc.SQLAlchemyError as e:
                conn.rollback()
                logger.error(f"Error executing delete transactions query: {e!s}")
                raise

    def update_item_cursor(self, item_id: str, cursor: str) -> None:
        """
        Update the cursor for an item.

        Parameters
        ----------
        item_id : str
            The id of the item.
        cursor : str
            The cursor for the item.

        """
        query = "UPDATE items SET transactions_cursor = :cursor WHERE plaid_item_id = :item_id"
        with self.engine.connect() as conn:
            try:
                conn.execute(sa.text(query), {"item_id": item_id, "cursor": cursor})
                conn.commit()
            except sa.exc.SQLAlchemyError as e:
                conn.rollback()
                logger.error(f"Error executing update cursor query: {e!s}")
                raise

    def close(self):
        """
        Close the connection to the database.

        Returns
        -------
        None

        """
        self.engine.dispose()

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
            f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}",
            pool_pre_ping=True,  # Enables connection health checks
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_size=3,  # Maximum number of connections to keep
            max_overflow=3,  # Maximum number of connections that can be created beyond pool_size
        )
        logger.info(f"Connected to database: {db_name}")

        return engine
