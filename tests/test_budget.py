"""Tests the budget."""

import numpy as np
import pandas as pd

from folioflex.budget import models
from folioflex.utils import config_helper

config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_budget.ini"
test_csv = config_helper.ROOT_PATH / "tests" / "files" / "test_budget.csv"


def test_create_features():
    """Checks if features are created."""
    train_df = pd.read_csv(test_csv)
    model = models.Classifier(train_df=train_df)

    # clean columns
    train_df["amount"] = model._clean_column(
        train_df["amount"],
        str_replace_comma=True,
        as_type_float=True,
    )
    train_df["name"] = model._clean_column(
        train_df["name"],
        str_replace_special=True,
        lower=True,
        as_type_str=True,
    )

    features, encoders = model._create_features(
        description=train_df["name"],
        amount=train_df["amount"],
        institution=train_df["plaid_institution_id"],
    )

    assert features.shape == (27, 60), "Shape mismatch"
    assert features.dtype == np.float64, "Data type mismatch"
    assert features.nnz == 1425, "Number of stored elements mismatch"
    assert features.format == "coo", "Sparse format mismatch"
