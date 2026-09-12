"""Tests the budget."""

import gensim.downloader as api
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from folioflex.budget import budget
from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)
config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_config.yml"
test_csv = config_helper.ROOT_PATH / "tests" / "files" / "test_budget.csv"


def test_create_features(budget_model, budget_df):
    """Checks if features are created."""
    train_df = budget_df[budget_df["label"].notnull()]
    train_df = budget_model.preprocess_data(train_df)
    features, encoders = budget_model._create_features(
        description=train_df["name"],
        amount=train_df["amount"],
        institution=train_df["plaid_institution_id"],
    )

    assert features.shape == (30, 61), "Shape mismatch"
    assert features.dtype == np.float64, "Data type mismatch"
    assert features.nnz == 1581, "Number of stored elements mismatch"
    assert features.format == "coo", "Sparse format mismatch"


def test_predictions(budget_model, budget_df):
    """Checks if predictions are made."""
    unlabeled_df = budget_df[budget_df["label"].isnull()]
    unlabeled_df = budget_model.preprocess_data(unlabeled_df)
    predict_df = budget_model.predict_labels(
        unlabeled_df=unlabeled_df, components=budget_model.components
    )

    assert predict_df.loc[3, "predicted_label"] == "groceries", (
        "A description of 'groceries' was not predicted correctly"
    )


def test_feature_countvectorizer():
    """Checks if the feature count vectorizer is correct."""
    vec = CountVectorizer(
        analyzer="word",
        token_pattern="[a-zA-Z_]{3,}",
        max_features=5000,
    )
    test_text = ["I pet a pet", "I own a pet"]
    X = vec.fit_transform(test_text)
    vocabulary = vec.get_feature_names_out().tolist()
    assert vocabulary == ["own", "pet"], "Vocabulary mismatch"
    assert X.toarray().tolist()[0] == [
        0,
        2,
    ], "First text has incorrect count, should be 0 'own' and 2 'pet'"
    assert X.toarray().tolist()[1] == [
        1,
        1,
    ], "Second text has incorrect count, should be 1 'own' and 1 'pet'"


def test_feature_embedding(budget_model):
    """Checks if the feature embedding is correct."""
    logger.info("Loading GloVe model...")
    glove_model = api.load("glove-wiki-gigaword-50")  # large glove model
    logger.info("GloVe model loaded.")
    description = ["purchase groceries", "buy food", "vacation"]
    results = np.array(
        [
            budget_model._document_to_avg_vector(text, glove_model)
            for text in description
        ]
    )

    # cosine similarity formula
    # https://www.geeksforgeeks.org/how-to-calculate-cosine-similarity-in-python/
    def cosine_similarity(vec1, vec2):
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    similarity_food = cosine_similarity(results[0], results[1])
    similarity_vacation = cosine_similarity(results[0], results[2])

    assert similarity_food > similarity_vacation, (
        "The cosine similarity shows that vacation is more similar "
        "to groceries than food. This is incorrect."
    )


def test_subscription(budget_df):
    """Checks if the subscription identification is correct."""
    budget_df["date"] = pd.to_datetime(budget_df["date"]).dt.date
    bdgt = budget.Budget(config_path="test_config.yml", budget="test")
    subscription_tbl = bdgt.identify_subscriptions(tx_df=budget_df)
    utils_occurs = subscription_tbl[subscription_tbl["Description"] == "utils"][
        "Occurrences"
    ]

    assert utils_occurs.values[0] == 3, "Utilities have 3 occurrences"


def test_subscription_active_only():
    """Checks that canceled subscriptions are only shown when asked for."""
    bdgt = budget.Budget(config_path="test_config.yml", budget="test")
    tx_df = pd.DataFrame(
        # billed monthly all year
        [
            {"date": f"2026-{m:02d}-05", "name": "current", "amount": 15.99}
            for m in range(1, 13)
        ]
        # billed monthly, then cancelled in March
        + [
            {"date": f"2026-{m:02d}-12", "name": "cancelled", "amount": 40.00}
            for m in range(1, 4)
        ]
    )

    active = bdgt.identify_subscriptions(tx_df=tx_df)
    assert set(active["Description"]) == {"current"}, (
        "A subscription that stopped being charged should be excluded by default"
    )

    every = bdgt.identify_subscriptions(tx_df=tx_df, active_only=False)
    assert set(every["Description"]) == {"current", "cancelled"}, (
        "active_only=False should still show past subscriptions"
    )
    assert not every[every["Description"] == "cancelled"]["Active"].iloc[0]


def test_subscription_no_matches():
    """Checks an empty result returns a frame rather than raising."""
    bdgt = budget.Budget(config_path="test_config.yml", budget="test")
    tx_df = pd.DataFrame([{"date": "2026-01-01", "name": "one off", "amount": 5}])

    subscriptions = bdgt.identify_subscriptions(tx_df=tx_df)
    assert subscriptions.empty
    assert "Occurrences" in subscriptions.columns


def test_preprocess_emoji():
    """Checks if emojis are removed from text."""
    test_text = "I love 🐶"
    bdgt = budget.Budget(config_path="test_config.yml", budget="test")
    clean_text = bdgt.modify_preprocess_emoji(test_text)
    assert clean_text == "I love  dog_face ", "Emoji was not removed from text"
