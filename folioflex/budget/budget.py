"""
Create a budget class that will provide methods to analyze a budget.

The initialization will take in a config file that will provide the budget
information.

Some methods that are included are:
    - get_transactions: Gets the transactions for the budget.
    - modify_transactions: Modifies the transactions for the budget.
    - budget_view: Provides a view of categories and their budget status.
    - display_budget_view: Displays a view of budgets in plotly.
    - display_income_view: Displays a view of income and expenses in plotly.
"""

import re

import emoji
import numpy as np
import pandas as pd
import plotly.express as px
import sqlalchemy as sa

from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


class Budget:
    """
    A class to represent a budget.

    Parameters
    ----------
    config_path : str
        the location of the config file
    budget : str
        the name of the budget to analyze

    """

    def __init__(
        self,
        config_path,
        budget,
    ):
        """Initialize the Portfolio class."""
        logger.info("Initializing Budget class.")
        self.config_dict = config_helper.get_config_options(config_path, budget)
        self.budgets = self.config_dict["budgets"]
        self.default = self.config_dict["default"]

    def get_transactions(self, engine=None):
        """
        Get the transactions for the budget.

        The transactions come from a database that uses Plaid to be populated.

        Parameters
        ----------
        engine : SQLAlchemy engine
            The engine to connect to the database.

        Returns
        -------
        tx_df : DataFrame
            The transactions for the budget.
                - id: transaction id
                - plaid_institution_id: institution id
                - official_name: institution name
                - date: date of transaction
                - name: description of transaction
                - amount: amount of transaction
                - category: category of transaction determined by account
                - primary_category: category of transaction determined by plaid
                - detailed_category: subcategory of transaction determined by plaid
                - pending: whether the transaction is pending
                - type: type of transaction
                - label: label of transaction that is determined by user

        """
        if engine is None:
            engine = self._create_engine()
        logger.info("Getting transactions.")
        # creating a dataframe of transactions that include
        # the account name, item name, and transaction name
        with engine.connect() as conn, conn.begin():
            tx_df = pd.read_sql_table("transactions_table", conn)
        with engine.connect() as conn, conn.begin():
            item_df = pd.read_sql_table("items_table", conn)
        with engine.connect() as conn, conn.begin():
            account_df = pd.read_sql_table("accounts_table", conn)
        # creating a grouped dataset
        tx_df = pd.merge(
            tx_df,
            account_df[["id", "official_name", "item_id"]],
            left_on="account_id",
            right_on="id",
            how="left",
            suffixes=[None, "_tmp"],
        )
        tx_df = pd.merge(
            tx_df,
            item_df[["id", "plaid_institution_id"]],
            left_on="item_id",
            right_on="id",
            how="left",
            suffixes=[None, "_tmp"],
        )
        tx_df = tx_df[
            [
                "id",
                "plaid_institution_id",
                "official_name",
                "date",
                "name",
                "amount",
                "category",
                "primary_category",
                "detailed_category",
                "pending",
                "type",
                "label",
            ]
        ].sort_values(by="date", ascending=False)
        tx_df["month"] = tx_df["date"].dt.strftime("%Y-%m")

        logger.info(f"Number of transactions: {len(tx_df)}")
        logger.info(
            f"Number of transactions that are pending: "
            f"{len(tx_df[tx_df['pending']==True])}"
        )

        return tx_df

    def modify_transactions(self, tx_df, columns_to_zero=None):
        """
        Modify the transactions for the budget.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions for the budget.
        columns_to_zero : set
            The columns to zero out the amount for.

        Returns
        -------
        tx_df : DataFrame
            The modified transactions for the budget.

        """
        if columns_to_zero is None:
            columns_to_zero = ["credit card", "transfer"]

        logger.info(f"Zeroing out amount for columns: {columns_to_zero}")
        tx_df = self.modify_zero_out_amount(tx_df, columns=columns_to_zero)
        logger.info("Extracting quoted text.")
        tx_df["name"] = tx_df["name"].apply(self.modify_extract_quoted_text)
        logger.info("Preprocessing emoji.")
        tx_df["name"] = tx_df["name"].apply(self.modify_preprocess_emoji)
        logger.info("Removing pending transactions.")
        tx_df = self.modify_remove_pending(tx_df)

        # if labels are not assigned create warning
        unassigned_labels = tx_df[tx_df["label"].isnull()]
        if len(unassigned_labels) > 0:
            logger.warning(
                f"Number of transactions without label assigned: "
                f"{len(unassigned_labels)} out of {len(tx_df)}"
            )
        else:
            logger.info(
                f"Number of transactions without label assigned: "
                f"{len(unassigned_labels)} out of {len(tx_df)}"
            )

        return tx_df

    def modify_zero_out_amount(self, tx_df, columns):
        """
        Zero out the amount for the given columns.

        Transactions such as transfers and credit card payments should not be
        included in the budget.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions for the budget.
        columns : list
            The columns to zero out the amount for.

        Returns
        -------
        tx_df : DataFrame
            The transactions with the amount zeroed out for the given columns.

        """
        condition = tx_df["label"].isin(columns)
        tx_df["amount"] = np.where(condition, 0, tx_df["amount"])
        return tx_df

    def modify_extract_quoted_text(self, column):
        """
        Extract the text between quotes.

        Parameters
        ----------
        column : str
            The column to extract the text from.

        Returns
        -------
        str
            The text between quotes.

        """
        quote_pattern = r'"([^"]*)"'
        match = re.search(quote_pattern, column)
        return match.group(1) if match else column

    def modify_preprocess_emoji(self, text):
        """
        Preprocess the emoji in the text.

        Parameters
        ----------
        text : str
            The text to preprocess.

        Returns
        -------
        str
            The text with the emoji preprocessed.

        """
        text_with_emoji = emoji.demojize(text, delimiters=(" ", " "))
        text_with_spaces = re.sub(
            r"(?<=\w)( :[a-zA-Z_]+:)(?=\w)", r" \1 ", text_with_emoji
        )
        return text_with_spaces

    def modify_remove_pending(self, tx_df):
        """
        Remove the pending transactions.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions for the budget.

        Returns
        -------
        tx_df : DataFrame
            The transactions with the pending transactions removed.

        """
        tx_df = tx_df[tx_df["pending"] == False]

        return tx_df

    def modify_custom_categorize(row):
        """
        Categorize the transaction.

        This is just used as an example of how to create a custom categorization
        function.

        Parameters
        ----------
        row : Series
            The row to categorize.

        Returns
        -------
        str
            The category of the transaction.

        """
        if "Test" in row["name"]:
            return "Test Category"
        if row["primary_category"] == "TRANSFER_OUT":
            return "Outgoing Transfer"
        if row["detailed_category"] == "TRANSFER_IN_ACCOUNT_TRANSFER":
            return "Incoming Transfer"
        return "OTHER"

    def budget_view(self, tx_df, target_date, exclude_labels=None):
        """
        Provide a view of categories and their budget status.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to view budget status for.
        target_date : str
            The date to view budget status for. Format: YYYY-MM.
        exclude_labels : list
            The labels to exclude from the budget view.

        Returns
        -------
        budget_df : DataFrame
            The budget status for each category.

        """
        budgets = self.config_dict["budgets"]
        if exclude_labels is not None:
            tx_df = tx_df[~tx_df["label"].isin(exclude_labels)]
            budgets = {k: v for k, v in budgets.items() if k not in exclude_labels}
        # grouping transactions
        grouped_transactions = (
            tx_df[tx_df["date"].dt.to_period("M") == target_date]
            .groupby("label")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=True)
        )
        # adding in the budget
        unused_keys = set(budgets.keys()) - set(grouped_transactions["label"])
        unused_keys_df = pd.DataFrame({"label": list(unused_keys)})
        grouped_transactions = pd.concat(
            [grouped_transactions, unused_keys_df], ignore_index=True
        )
        grouped_transactions = grouped_transactions.fillna(0)
        grouped_transactions["budget"] = grouped_transactions["label"].map(budgets)
        grouped_transactions["budget"] = grouped_transactions["budget"].fillna(
            float(self.config_dict["default"])
        )
        # providing a total
        totals = grouped_transactions.sum(numeric_only=True).to_frame().T
        totals["label"] = "TOTAL"
        budget_df = pd.concat([grouped_transactions, totals], ignore_index=True)

        # flipping the sign if the budget is negative and switching back
        # after the calculations
        budget_df["budget_flag"] = np.where(budget_df["budget"] < 0, -1, 1)
        for column in ["budget", "amount"]:
            budget_df[column] = budget_df[column] * budget_df["budget_flag"]
        budget_df["amount_diff"] = budget_df["budget"] - budget_df["amount"]

        # calculating the amount remaining or over budget that has been spent
        budget_df["remaining_budget"] = budget_df.apply(
            lambda row: min(row["budget"], row["amount_diff"])
            if row["amount_diff"] >= 0
            else 0,
            axis=1,
        )
        budget_df["over_budget"] = budget_df["amount_diff"].apply(
            lambda x: -x if x < 0 else 0
        )
        budget_df["amount_up_to_budget"] = budget_df.apply(
            lambda row: row["amount"] if row["amount_diff"] >= 0 else row["budget"],
            axis=1,
        )

        # flipping the sign back
        for column in [
            "amount",
            "amount_up_to_budget",
            "budget",
            "over_budget",
            "remaining_budget",
        ]:
            budget_df[column] = budget_df[column] * budget_df["budget_flag"]

        return budget_df

    def display_budget_view(self, budget_df):
        """
        Display the budget view as a bar chart.

        Parameters
        ----------
        budget_df : DataFrame
            The budget table to visualize.

        Returns
        -------
        fig : Figure
            The budget view as a bar chart.

        """
        colors = ["blue", "red", "lightgray"]
        fig = px.bar(
            budget_df,
            x=["amount_up_to_budget", "over_budget", "remaining_budget"],
            y="label",
            orientation="h",
            title="Expenses vs. Budget by Category",
            labels={"value": "value", "label": "label"},
            color_discrete_sequence=colors,
            hover_data=["amount", "budget"],
        )

        fig.update_layout(height=600)
        return fig

    def display_income_view(self, tx_df):
        """
        Display the income view as a line chart.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to view income status for.

        Returns
        -------
        fig : Figure
            The budget view as a bar chart.

        """
        grouped_data = tx_df.groupby(["month"])["amount"].sum().reset_index()
        fig = px.line(
            grouped_data,
            x="month",
            y="amount",
            title="Monthly Expenses",
            labels={"month": "Month", "amount": "Amount"},
        )

        return fig

    def display_compare_expenses_view(self, tx_df, target_date=None, avg_months=12):
        """
        Display the compare expenses view as a line chart.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to view income status for.
        target_date : str
            The date to view budget status for. Format: YYYY-MM.
        avg_months : int
            The number of months to average over for a comparison.

        Returns
        -------
        fig : Figure
            The budget view as a line chart.

        """
        if target_date is None:
            target_date = tx_df["date"].max().strftime("%Y-%m")

        # Set the current month and prior month
        current_month = target_date
        prior_month = (
            pd.to_datetime(current_month) - pd.DateOffset(months=1)
        ).strftime("%Y-%m")

        # remove income transactions
        tx_df = tx_df[~tx_df["label"].isin(["income"])].sort_values(
            by="date", ascending=True
        )

        # Filter data for the current and prior months
        current_month_data = (
            tx_df[tx_df["date"].dt.to_period("M") == current_month]
            .groupby(tx_df["date"].dt.day)["amount"]
            .sum()
            .cumsum()
            .reset_index()
        )
        prior_month_data = (
            tx_df[tx_df["date"].dt.to_period("M") == prior_month]
            .groupby(tx_df["date"].dt.day)["amount"]
            .sum()
            .cumsum()
            .reset_index()
        )
        current_month_data["name"] = "Current Month"

        lookback_data = tx_df[
            (tx_df["date"] < pd.to_datetime(current_month))
            & (
                tx_df["date"]
                >= (pd.to_datetime(current_month) - pd.DateOffset(months=avg_months))
            )
        ]
        lookback_data_sum = (
            lookback_data.groupby(lookback_data["date"])["amount"].sum().reset_index()
        )

        lookback_data_sum = (
            lookback_data_sum.groupby(lookback_data_sum["date"].dt.day)["amount"]
            .mean()
            .cumsum()
            .reset_index()
        )

        # Plotting
        fig = px.line(
            current_month_data,
            x="date",
            y="amount",
            title="Cumulative Spending Comparison",
            labels={"date": "Day", "amount": "Cumulative Spending"},
            color_discrete_sequence=["orange"],
            color="name",
        )
        fig.add_scatter(
            x=prior_month_data["date"],
            y=prior_month_data["amount"],
            mode="lines",
            name="Prior Month",
            line={"color": "peachpuff"},
        )
        fig.add_scatter(
            x=lookback_data_sum["date"],
            y=lookback_data_sum["amount"],
            mode="lines",
            name=f"Average {avg_months}-Month",
            line={"color": "gray"},
        )

        return fig

    def category_tx_view(self, tx_df, target_date, category):
        """
        Display the transactions view as a table.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to view.
        target_date : str
            The date to view transactions for. Format: YYYY-MM.
        category : str
            The category to view transactions for.

        Returns
        -------
        cat_tx_df : DataFrame
            The category of transactions view as a table.

        """
        cat_tx_df = tx_df[
            (tx_df["date"].dt.to_period("M") == target_date)
            & (tx_df["label"].str.contains(category))
        ].sort_values(by="amount", ascending=False)
        return cat_tx_df

    def update_labels_db(self, tx_df, engine=None, label_column="label"):
        """
        Update the label in the database.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to update the label for.
        engine : SQLAlchemy engine
            The engine to connect to the database.
        label_column : str
            The column in the DataFrame that will be used to update the label.

        Returns
        -------
        None

        """
        if engine is None:
            engine = self._create_engine()
        logger.info("Updating labels in database.")
        rows_updated = 0
        with engine.connect() as conn:
            for _, row in tx_df.iterrows():
                if pd.isna(row[label_column]):
                    update_label_query = sa.text(
                        """
                        UPDATE public.transactions_table
                        SET "label" = NULL
                        WHERE id = :id;
                    """
                    )
                    executed = conn.execute(update_label_query, {"id": row["id"]})
                else:
                    update_label_query = sa.text(
                        """
                        UPDATE public.transactions_table
                        SET "label" = :label
                        WHERE id = :id;
                    """
                    )
                    executed = conn.execute(
                        update_label_query,
                        {"label": row[label_column], "id": row["id"]},
                    )
                rows_updated = rows_updated + executed.rowcount
            conn.commit()
        logger.info(f"Rows updated: {rows_updated}")

    def _create_engine(self):
        """
        Create an engine.

        Returns
        -------
        engine : SQLAlchemy engine
            The engine to connect to the database.

        """
        db_user = self.config_dict.get("db_user", None)
        db_pass = self.config_dict.get("db_pass", None)
        db_host = self.config_dict.get("db_host", None)
        db_name = self.config_dict.get("db_name", None)
        db_port = self.config_dict.get("db_port", None)

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

        logger.info("Connecting to database.")
        engine = sa.create_engine(
            f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        )
        return engine
