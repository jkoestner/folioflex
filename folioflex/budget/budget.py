"""
Reviews budget calculations and dashboard for transactions.

Some modules that are included are:
    - budget_view: Provides a view of categories and their budget status.
"""

import logging
import logging.config
import os

import numpy as np
import pandas as pd

from folioflex.utils import config_helper

# create logger
logging.config.fileConfig(
    os.path.join(config_helper.CONFIG_PATH, "logging.ini"),
)
logger = logging.getLogger(__name__)


def budget_view(transaction_df, budget, min_date):
    """
    Provide a view of categories and their budget status.

    Parameters
    ----------
    transaction_df : DataFrame
        The transactions to view budget status for.
    budget : dict
        Budgets for each category.
    min_date : str
        The date to view budget status for. Format: YYYY-MM-DD.

    Returns
    -------
    budget_df : DataFrame
        The budget status for each category.
    """
    # filter and calculate the sum for each category
    budget_df = (
        transaction_df[transaction_df["date"] >= min_date]
        .groupby("primary_category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=True)
    )
    totals = budget_df.sum(numeric_only=True).to_frame().T
    totals["primary_category"] = "TOTAL"
    budget_df = pd.concat([budget_df, totals], ignore_index=True)
    budget_df["budget"] = budget

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
        lambda row: row["amount"] if row["amount_diff"] >= 0 else row["budget"], axis=1
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
