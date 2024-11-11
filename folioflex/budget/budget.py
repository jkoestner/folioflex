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
from typing import Any, Dict, List, Optional, Union

import emoji
import numpy as np
import pandas as pd
import plotly.express as px

from folioflex.utils import config_helper, custom_logger, database

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
        config_path: str,
        budget: str,
    ) -> None:
        """Initialize the Portfolio class."""
        logger.info("Initializing Budget class.")
        self.config_path = config_path
        self.config_dict = config_helper.get_config_options(
            config_path, "budgets", budget
        )
        self.budgets = self.config_dict["budgets"]
        self.default = self.config_dict["default"]
        self.budget = budget
        self.model = self.config_dict.get("model", None)

    def get_transactions(
        self, engine: Optional[Any] = None, user: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get the transactions for the budget.

        The transactions come from a database that uses Plaid to be populated.

        Parameters
        ----------
        engine : SQLAlchemy engine
            The engine to connect to the database.
        user : str, optional
            The user to get the transactions for.

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
            engine = database.Engine(self.config_path)
        if user is None:
            user = self.config_dict.get("user", None)
        logger.info("Getting transactions.")
        # creating a dataframe of transactions that include
        # the account name, item name, and transaction name
        user_df = engine.read_table("users_table")
        item_df = engine.read_table("items_table")
        account_df = engine.read_table("accounts_table")
        tx_df = engine.read_table("transactions_table")
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
            item_df[["id", "plaid_institution_id", "user_id"]],
            left_on="item_id",
            right_on="id",
            how="left",
            suffixes=[None, "_tmp"],
        )
        tx_df = pd.merge(
            tx_df,
            user_df[["id", "username"]],
            left_on="user_id",
            right_on="id",
            how="left",
            suffixes=[None, "_tmp"],
        )
        if user is not None:
            tx_df = tx_df[tx_df["username"] == user]
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

        The modifications include:
          - Zero out the amount for the given columns
          - Extract the text between quotes
          - Preprocess the emoji in the text
          - Remove the pending transactions.

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

    def identify_subscriptions(self, tx_df):
        """
        Identify possible subscriptions in the transactions.

        The subscriptions are identified by the name and also the amount. If
        the amount is similar for multiple transactions, and there are at least
        a set amount of transcations, then it is likely a subscription.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to identify subscriptions for.

        Returns
        -------
        subscriptions : DataFrame
            The subscriptions identified in the transactions.

        """
        # default values
        min_transactions = 3
        interval_std_threshold = 5
        amount_std_threshold = 0.1

        # group data by name
        grouped_df = tx_df.groupby("name")

        # identify subscriptions
        subscriptions = []
        for name, group in grouped_df:
            if len(group) < min_transactions:
                continue

            # calculating the intervals and ensure they are regular
            intervals = group["date"].diff().dropna().dt.days
            regular = intervals.std() <= interval_std_threshold

            # calculate the amount and ensure it is consistent
            amount_mean = group["amount"].mean()
            if amount_mean == 0:
                continue
            relative_std = group["amount"].std() / amount_mean
            consistent_amount = relative_std <= amount_std_threshold

            # get the last date and amount
            last_date = group["date"].max()
            last_amount = group[group["date"] == last_date]["amount"].values[0]

            if regular and consistent_amount:
                subscriptions.append(
                    {
                        "Description": name,
                        "Occurrences": len(group),
                        "Mean Interval (Days)": intervals.mean(),
                        "Amount Mean": group["amount"].mean(),
                        "Amount Std Dev": group["amount"].std(),
                        "Last Date": last_date,
                        "Last Amount": last_amount,
                    }
                )

        subscriptions_df = pd.DataFrame(subscriptions)
        subscriptions_df = subscriptions_df.sort_values(
            by="Occurrences", ascending=False
        )

        return subscriptions_df

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

    def display_category_trend(self, tx_df, category):
        """
        Display the category trend view as a bar chart.

        Parameters
        ----------
        tx_df : DataFrame
            The transactions to view income status for.
        category : str
            The category to view the trend for.

        Returns
        -------
        fig : Figure
            The category trend view as a line chart.

        """
        # filter data for category
        category_df = tx_df[tx_df["label"] == category]
        category_df = category_df.groupby(["month"])["amount"].sum().reset_index()
        if len(category_df) == 0:
            logger.warning(f"No transactions found for category: {category}")
            return None

        # budgets
        category_budget = self.budgets.get(category, 0)
        average_budget = category_df["amount"].mean()
        twelve_month_avg = category_df["amount"].rolling(window=12).mean()

        # create bar chart
        fig = px.bar(
            category_df,
            x="month",
            y="amount",
            title=f"'{category}' Spending Trend",
            labels={"month": "Month", "amount": "Amount"},
            color_discrete_sequence=["blue"],
        )

        # add budget line
        fig.add_scatter(
            x=category_df["month"],
            y=[category_budget] * len(category_df),
            mode="lines",
            line={"color": "red", "dash": "dash"},
            name="Budget",
        )

        # add average line
        fig.add_scatter(
            x=category_df["month"],
            y=[average_budget] * len(category_df),
            mode="lines",
            line={"color": "black", "dash": "dash"},
            name="Average",
        )

        # add 12 month average line
        fig.add_scatter(
            x=category_df["month"],
            y=twelve_month_avg,
            mode="lines",
            line={"color": "green", "dash": "dash"},
            name="12-Month Average",
        )

        return fig

    def category_tx_view(
        self,
        tx_df,
        target_date,
        category,
        columns=None,
    ):
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
        columns : list (optional)
            The columns to view in the table.

        Returns
        -------
        cat_tx_df : DataFrame
            The category of transactions view as a table.

        """
        if columns is None:
            columns = [
                "date",
                "amount",
                "name",
                "label",
                "official_name",
            ]

        cat_tx_df = tx_df[
            (tx_df["date"].dt.to_period("M") == target_date)
            & (tx_df["label"].str.contains(category))
        ].sort_values(by="date", ascending=False)
        cat_tx_df = cat_tx_df[columns]
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
            engine = database.Engine(self.config_path)
        logger.info("Updating labels in database.")

        # filter the table
        tx_df = tx_df[[label_column, "id"]]

        tx_df = tx_df.rename(columns={label_column: "label"})
        engine.bulk_update(
            tx_df=tx_df, table_name="transactions_table", where_column="id"
        )

        logger.info(f"Rows updated: {len(tx_df)}")
