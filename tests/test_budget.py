"""Tests the budget."""

import gensim.downloader as api
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from folioflex.budget import models
from folioflex.utils import config_helper

config_path = config_helper.ROOT_PATH / "tests" / "files" / "test_budget.ini"
test_csv = config_helper.ROOT_PATH / "tests" / "files" / "test_budget.csv"

df = pd.read_csv(test_csv)
train_df = df[df["label"].notnull()]
model = models.Classifier(train_df=train_df)
model.create_model()


def test_create_features():
    """Checks if features are created."""
    train_df = df[df["label"].notnull()]
    train_df = model.preprocess_data(train_df)
    features, encoders = model._create_features(
        description=train_df["name"],
        amount=train_df["amount"],
        institution=train_df["plaid_institution_id"],
    )

    assert features.shape == (27, 60), "Shape mismatch"
    assert features.dtype == np.float64, "Data type mismatch"
    assert features.nnz == 1425, "Number of stored elements mismatch"
    assert features.format == "coo", "Sparse format mismatch"


def test_predictions():
    """Checks if predictions are made."""
    unlabeled_df = df[df["label"].isnull()]
    unlabeled_df = model.preprocess_data(unlabeled_df)
    predict_df = model.predict_labels(
        unlabeled_df=unlabeled_df, components=model.components
    )

    assert (
        predict_df.loc[0, "predicted_label"] == "groceries"
    ), "A description of 'groceries' was not predicted correctly"


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


def test_feature_embedding():
    """Checks if the feature embedding is correct."""
    glove_model = api.load("glove-wiki-gigaword-50")
    description = ["purchase groceries", "buy food", "vacation"]
    results = np.array(
        [model._document_to_avg_vector(text, glove_model) for text in description]
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
