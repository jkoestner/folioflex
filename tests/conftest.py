"""Shared fixtures for tests."""

import pandas as pd
import pytest

from folioflex.budget import models
from folioflex.portfolio import portfolio
from folioflex.utils import config_helper

config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_config.yml"
test_csv = config_helper.ROOT_PATH / "tests" / "files" / "test_budget.csv"


# adding fixtures to avoid startup lag when loading the tests
@pytest.fixture(scope="session")
def pf():
    """Return a Portfolio instance for testing."""
    return portfolio.Portfolio(config_path=config_path, portfolio="test")


@pytest.fixture(scope="session")
def config_dict():
    """Return the configuration dictionary for testing."""
    return config_helper.get_config_options(config_path, "investments", "test")


@pytest.fixture(scope="session")
def budget_model():
    """Return a Budget model instance for testing."""
    df = pd.read_csv(test_csv)
    train_df = df[df["label"].notnull()]
    model = models.Classifier(train_df=train_df)
    model.create_model()
    return model


@pytest.fixture(scope="session")
def budget_df():
    """Return the budget dataframe for testing."""
    return pd.read_csv(test_csv)
