"""Module for handling loans."""

import math
from typing import TYPE_CHECKING, Optional, Union

import pandas as pd

from folioflex.utils import config_helper, custom_logger

pd.options.display.float_format = "{:,.2f}".format

logger = custom_logger.setup_logging(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from folioflex.utils.database import Engine


def get_loan_df(
    config_path: Union[str, "Path"],
    loan: Optional[str] = None,
    engine: Optional["Engine"] = None,
    user: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get loan df.

    Parameters
    ----------
    config_path : str
        The location of the config file.
    loan : str, optional
        The name of the loan.
    engine : SQLAlchemy engine
        The engine to connect to the database. Used to get the credit card value.
    user : str, optional
        The name of the user. Used if engine is provided to get the credit card value.
        Also used to filter the loans of a specific user.

    Returns
    -------
    loan_df : pd.DataFrame
        A dataframe with the loan info.

    """
    items = []
    rows = []

    # get the list of loans to use for the calculations
    if loan:
        items.append(loan)
    else:
        items += list(config_helper.get_config_options(config_path, "loans").keys())
    items = [item for item in items if item != "users"]

    # process each loan
    for item in items:
        params = config_helper.get_config_options(config_path, "loans", item)
        payments_left = get_payments_left(config_path, loan=item)
        if payments_left is None:
            logger.error(f"No interest as there was no payments left for {item}.")
            interest_left = None
        else:
            interest_left = get_interest(
                current_loan=params["current_loan"],
                payments_left=payments_left,
                payment_amount=params["monthly_payment"],
            )
        rows.append(
            {
                "loan": item,
                "original loan": float(params["original_loan"]),
                "nominal_annual_interest": params["nominal_annual_interest"],
                "monthly_payment": float(params["monthly_payment"]),
                "current_loan": float(params["current_loan"]),
                "payments_left": payments_left,
                "interest_left": interest_left,
            }
        )

    # add in the credit card value
    if engine:
        credit_card_value = get_credit_card_value(engine, user=user)
        rows.append(
            {
                "loan": "credit card",
                "original loan": None,
                "nominal_annual_interest": None,
                "monthly_payment": None,
                "current_loan": credit_card_value,
                "payments_left": None,
                "interest_left": None,
            }
        )
    loan_df = pd.DataFrame(rows)

    # filter by user
    if user:
        user_loans = config_helper.get_config_options(
            config_path, "loans", "users"
        ).get(user, None)
        loan_df = loan_df[loan_df["loan"].isin([*user_loans, "credit card"])]

    # sort and total
    loan_df = loan_df.sort_values(by="loan", ascending=False)
    loan_df.loc["total"] = loan_df.select_dtypes("number").sum()

    return loan_df


def get_payments_left(
    config_path: Optional[Union[str, "Path"]] = None,
    loan: Optional[str] = None,
    current_loan: Optional[float] = None,
    payment_amount: Optional[float] = None,
    interest: Optional[float] = None,
) -> Union[float, None]:
    """
    Get the info of a loan.

    We use the nominal interest rate to calculate the payments left.
      - nominal interest is the interest rate without the effect of compounding
      - effective interest rate is the interest rate with the effect of compounding
      - real interest rate is the interest rate with the effect of inflation

    Parameters
    ----------
    config_path : str
        The location of the config file.
    loan : str, optional
        The name of the loan.
    current_loan : float, optional
        The current loan amount.
    payment_amount : float, optional
        The payment amount.
    interest : float, optional
        The interest rate.

    Returns
    -------
    payments_left : float
        The number of payments left on the loan.

    References
    ----------
    - https://brownmath.com/bsci/loan.htm

    """
    if config_path:
        params = config_helper.get_config_options(config_path, "loans", loan)
        required_keys = ["current_loan", "monthly_payment", "nominal_annual_interest"]
        if not all(key in params for key in required_keys):
            missing_keys = [key for key in required_keys if key not in params]
            logger.error(
                f"The keys {missing_keys} should be in the config file and were not "
                f"found in the loan '{loan}'."
            )
            return None
        current_loan = params["current_loan"]
        payment_amount = params["monthly_payment"]
        interest = params["nominal_annual_interest"] / 12 / 100

    if current_loan is None or payment_amount is None or interest is None:
        logger.error(
            "The config_path or the current_loan, payment_amount, and interest "
            "should be provided."
        )
        return None

    # checks
    if interest >= 1:
        logger.error(
            "The interest rate should be less than 1 and be written as "
            "as percentage."
        )
        return None

    # get the payments left
    payments_left = math.log10(
        1 / (1 - (current_loan * interest) / payment_amount)
    ) / math.log10(1 + interest)

    return payments_left


def get_payment_amount(
    current_loan: float,
    payments_left: float,
    interest: float,
) -> Union[float, None]:
    """
    Get the amount of the payment.

    We use the nominal interest rate to calculate the payments left.
      - nominal interest is the interest rate without the effect of compounding
      - effective interest rate is the interest rate with the effect of compounding
      - real interest rate is the interest rate with the effect of inflation

    Parameters
    ----------
    current_loan : float
        The current loan amount.
    payments_left : float
        The monthly payment.
    interest : float
        The interest rate.

    Returns
    -------
    payment_amount : float
        The amount of the payments

    References
    ----------
    - https://brownmath.com/bsci/loan.htm

    """
    # checks
    if interest >= 1:
        logger.error(
            "The interest rate should be less than 1 and be written as "
            "as percentage."
        )
        return None

    # get the payments left
    payment_amount = (current_loan * interest) / (1 - (1 + interest) ** -payments_left)

    return payment_amount


def get_interest(
    current_loan: float,
    payments_left: float,
    payment_amount: float,
) -> float:
    """
    Get the interest that will be paid.

    Parameters
    ----------
    current_loan : float
        The current loan amount.
    payments_left : float
        The amount of payments left.
    payment_amount : float
        The monthly payment.

    Returns
    -------
    interest : float
        The amount of interest that will be paid.

    """
    interest = (payments_left * payment_amount) - current_loan

    return interest


def get_credit_card_value(engine: "Engine", user: Optional[str] = None) -> float:
    """
    Get the value of the loan account.

    Parameters
    ----------
    engine : SQLAlchemy engine
        The engine to connect to the database.
    user : str, optional
        The name of the user.

    Returns
    -------
    loan_value : float
        The value of the loan accounts.

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
    account_df = account_df[account_df["subtype"] == "credit card"]
    loan_value = account_df["current_balance"].sum()

    return loan_value
