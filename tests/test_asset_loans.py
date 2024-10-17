"""Tests the assets and loans."""

import math

from folioflex.portfolio import assets, loans
from folioflex.utils import config_helper

config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_config.yml"


def test_get_loan_df():
    """Tests the get_loan_df function."""
    loan_df = loans.get_loan_df(config_path, user="user1")

    assert loan_df[loan_df["loan"] == "house"]["original loan"].values[0] == 500000
    assert loan_df[loan_df["loan"] == "house"]["current_loan"].values[0] == 400000
    assert loan_df[loan_df["loan"] == "house"]["monthly_payment"].values[0] == 2000
    assert (
        loan_df[loan_df["loan"] == "house"]["nominal_annual_interest"].values[0] == 5.0
    )
    assert (
        round(loan_df[loan_df["loan"] == "house"]["payments_left"].values[0], 2)
        == 430.92
    )
    assert (
        round(loan_df[loan_df["loan"] == "house"]["interest_left"].values[0], 2)
        == 461835.06
    )


def test_get_payments_left():
    """Tests the get_payments_left function."""
    i_annual = 5
    i = i_annual / 100 / 12
    A = 400000
    P = 2000
    payments_left = loans.get_payments_left(
        current_loan=A,
        payment_amount=P,
        interest=i,
    )
    calc_payments_left = -math.log10(1 - i * A / P) / math.log10(1 + i)
    assert payments_left == calc_payments_left


def test_get_payment_amount():
    """Tests the get_payment_amount function."""
    i_annual = 5
    i = i_annual / 100 / 12
    A = 400000
    N = 430.92
    payment_amount = loans.get_payment_amount(
        current_loan=A,
        payments_left=N,
        interest=i,
    )
    calc_payment_amount = (i * A) / (1 - (1 + i) ** -N)
    assert payment_amount == calc_payment_amount


def test_get_interest():
    """Tests the get_interest function."""
    A = 400000
    P = 2000
    N = 430.92
    interest_left = loans.get_interest(
        current_loan=A,
        payments_left=N,
        payment_amount=P,
    )
    calc_interest_left = P * N - A
    assert interest_left == calc_interest_left
