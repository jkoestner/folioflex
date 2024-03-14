"""Creates categories for transactions."""

import os

import gensim.downloader as api
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, StandardScaler

from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


class Classifier:
    """
    A Classifier Class that predicts labels with a given transactional dataset.

    The classifier requires a training dataset be provided with the necessary columns.
    It should be noted that to be able to predict on a new dataset the training set
    needs to contain at least one of the values from the prediciton dataset.

    Parameters
    ----------
    train_df : DataFrame
        Dataframe of transactions that need to be classified. The DataFrame
        needs the following items
            - amount: the amount of the transaction
            - name: the description of the transactions
            - plaid_institution_id: the account associated with transaction
            - label: the category of the transactions

    """

    def __init__(
        self,
        train_df,
    ):
        self.train_df = train_df
        self.components = None

    def create_model(self, test_size=0.1):
        """
        Create a classifier model for predicting labels.

        Parameters
        ----------
        test_size : float
           The percentage of dataframe that is set aside for testing

        Returns
        -------
        components : dict
           contains a number of components from the output of the test
              - vec
              - glove_model
              - scalar
              - le
              - output_transformer
              - clf
              - test_results

        """
        train_df = self.train_df.copy()
        logger.info(f"creating a classifier model with {len(train_df)} rows")

        # cleaning up columns and reformatting
        #
        # amount column needs to be float instead of string
        # name column removes special characters such as ["]
        # augmenting columns that have little data by repeating them
        # format the target_variable (Y)
        logger.info("cleaning up data")
        train_df = self.preprocess_data(train_df)
        train_df = self._duplicate_sparse_data_rows(train_df, min_count=10)

        # x values
        logger.info("creating the features")
        features, encoders = self._create_features(
            description=train_df["name"],
            amount=train_df["amount"],
            institution=train_df["plaid_institution_id"],
        )

        # y values
        output_transformer = OrdinalEncoder()
        Y = output_transformer.fit_transform(train_df[["label"]])

        # split into train/test
        logger.info("training the data with logistic regression")
        X_train, X_test, Y_train, Y_test = train_test_split(
            features, Y.ravel(), test_size=test_size, random_state=2
        )

        # fit the data
        # tried MultinomialNB(), but not as accurate
        clf = LogisticRegression(max_iter=300)
        clf.fit(X_train, Y_train)

        # predict the data
        logger.info("creating predicitons and calculating accuracy")
        y_pred = clf.predict(X_test)
        y_pred_prob = clf.predict_proba(X_test)
        accuracy = accuracy_score(Y_test, y_pred)
        logger.info(f"Accuracy: {accuracy * 100:.2f}%")

        # encoders from feature creation
        vec = encoders["vec"]
        glove_model = encoders["glove_model"]
        scaler = encoders["scaler"]
        le = encoders["le"]

        logger.info("calculating test results which are in components")
        test_description_vec = X_test[:, : len(vec.get_feature_names_out())]
        test_description = vec.inverse_transform(test_description_vec)
        test_amount = X_test[:, -2].toarray()
        test_amount = scaler.inverse_transform(test_amount)
        test_institution = X_test[:, -1].toarray()
        y_pred_labels = output_transformer.inverse_transform(y_pred.reshape(-1, 1))
        Y_test_labels = output_transformer.inverse_transform(Y_test.reshape(-1, 1))
        y_pred_confidence = np.amax(y_pred_prob, axis=1)
        test_results = pd.DataFrame(
            {
                "description": [" ".join(text) for text in test_description],
                "predicted_label": y_pred_labels.ravel(),
                "correct_label": Y_test_labels.ravel(),
                "predicted_prob": y_pred_confidence,
                "amount": test_amount.ravel(),
                "institution": test_institution.ravel(),
            }
        )

        components = {
            "date": pd.Timestamp.now(),
            "accuracy": accuracy,
            "vec": vec,
            "glove_model": glove_model,
            "scaler": scaler,
            "le": le,
            "output_transformer": output_transformer,
            "clf": clf,
            "test_results": test_results,
        }

        self.components = components

        return components

    def save_model(self, model_name="components.pkl"):
        """
        Save the model to a file.

        Parameters
        ----------
        model_name : str
           the name of the file to save the model to

        """
        if not self.components:
            logger.warning("no components to save")
            return
        model_path = os.path.join(config_helper.CONFIG_PATH, "models", model_name)
        logger.info(f"saving model to {model_path}")
        joblib.dump(self.components, model_path)

    def load_model(self, model_name="components.pkl"):
        """
        Load the model from a file.

        Parameters
        ----------
        model_name : str
           the name of the file to load the model from

        """
        model_path = os.path.join(config_helper.CONFIG_PATH, "models", model_name)
        logger.info(f"loading model from {model_path}")
        self.components = joblib.load(model_path)

    def predict_labels(self, unlabeled_df, components):
        """
        Predict labels based on model.

        Parameters
        ----------
        unlabeled_df : DataFrame
           the dataframe to create labels for
        components : dict
           the dictionary that contains the encoders and models

        Returns
        -------
        predicted_df : DataFrame
           the dataframe that contains the predicted labels

        """
        if unlabeled_df.empty:
            logger.warning("the dataframe is empty")
            return unlabeled_df
        predicted_df = unlabeled_df.copy()
        logger.info(f"predicting labels for {len(predicted_df)} rows")
        predicted_df = self.preprocess_data(predicted_df)

        desription = predicted_df["name"]
        amount = predicted_df["amount"]
        institution = predicted_df["plaid_institution_id"]

        logger.info("creating features on the prediction dataframe")
        features, encoders = self._create_features(
            desription, amount, institution, components
        )

        logger.info("calculating the predictions")
        # Make a prediction
        clf = components["clf"]
        output_transformer = components["output_transformer"]
        prediction = clf.predict(features)
        prediction_proba = clf.predict_proba(features)
        prediction_label = output_transformer.inverse_transform(
            prediction.reshape(-1, 1)
        )

        logger.info("outputting to dataframe")
        predicted_df["predicted_label"] = prediction_label.ravel()
        predicted_df["prediction_proba"] = np.amax(prediction_proba, axis=1).ravel()

        return predicted_df

    def preprocess_data(self, df):
        """
        Preprocess the data for the model.

        Parameters
        ----------
        df : DataFrame
           the dataframe to preprocess

        Returns
        -------
        df : DataFrame
           the dataframe that has been preprocessed

        """
        logger.info("preprocessing data")
        df = df.copy()
        df["amount"] = self._clean_column(
            df["amount"],
            str_replace_comma=True,
            as_type_float=True,
        )
        df["name"] = self._clean_column(
            df["name"],
            str_replace_special=True,
            lower=True,
            as_type_str=True,
        )
        return df

    def _document_to_avg_vector(self, text, model):
        """
        Provide a word embedding average for words.

        Parameters
        ----------
        text : str
           the transaction description to analyze
        model : LLM
           a large language model to provide similarities between words

        Returns
        -------
        null : array
           array of average word embeddings

        """
        words = text.split()
        word_embeddings = [model[word] for word in words if word in model]
        if not word_embeddings:
            return np.zeros(model.vector_size)
        return np.mean(word_embeddings, axis=0)

    def _create_features(self, description, amount, institution, components=None):
        """
        Create features for model.

        glove:
          - Provides word embeddings for the "description" field.
            Uses a Global Vectors (glove) model for word representation. The
            wikiword model is used currently for being lightweight and fast.
        vectorizer:
          - Provides a word count for the "description" field that's output to
            a sparse matrix.
        scalar:
          - Provides a scaled amount of the "amount" field.
        le:
          - Provides a label encoding for the "institution" field.

        Parameters
        ----------
        description : series
           the series that has the transaction description
        amount : series
           the series that has the transaction amount
        institution : series
           the series that has the transaction institution
        components : dict
           the dictionary of components. the compenents need are:
              - glove_model
              - vec
              - scalar
              - le

        """
        # Use the components from the trained model to transform new data
        if components:
            # encoders
            glove_model = components["glove_model"]
            vec = components["vec"]
            scaler = components["scaler"]
            le = components["le"]

            # transforming
            amount_scaled = scaler.transform(amount.to_frame())
            description_word_count = vec.transform(description)
            institution_encoded = le.transform(institution)

        else:
            # encoders
            # other models to consider
            # "word2vec-google-news-300" which is a larger model
            glove_model = api.load("glove-wiki-gigaword-50")
            vec = CountVectorizer(
                analyzer="word",
                token_pattern="[a-zA-Z_]{3,}",
                max_features=5000,
                # ngram_range = (1,3) # 3 words can be slow
            )

            scaler = StandardScaler()
            le = LabelEncoder()

            # fitting
            amount_scaled = scaler.fit_transform(amount.to_frame())
            description_word_count = vec.fit_transform(description)
            institution_encoded = le.fit_transform(institution)

        description_embedding = csr_matrix(
            np.array(
                [
                    self._document_to_avg_vector(text, glove_model)
                    for text in description
                ]
            )
        )
        institution_encoded = institution_encoded.reshape(-1, 1)

        features = hstack(
            [
                description_word_count,
                description_embedding,
                amount_scaled,
                institution_encoded,
            ]
        )

        encoders = {
            "vec": vec,
            "glove_model": glove_model,
            "scaler": scaler,
            "le": le,
        }

        return features, encoders

    def _duplicate_sparse_data_rows(self, df, min_count=10):
        """
        Repeat data that have a limited label count.

        Need to duplicate data that has limited label count due to training
        needing at least one value to train on.

        Parameters
        ----------
        df : DataFrame
            The DataFrame to duplicate transactions
        min_count : int
            The min number of records a label should have

        Returns
        -------
        df_augmented : DataFrame
            The DataFrame with added transactions.

        """
        label_counts = df.groupby("label").size()
        labels_to_augment = label_counts[label_counts < min_count].index.tolist()

        augmented_rows = []
        for label in labels_to_augment:
            label_data = df[df["label"] == label]
            num_duplicates_needed = min_count - len(label_data)
            duplicates = label_data.sample(n=num_duplicates_needed, replace=True)
            augmented_rows.append(duplicates)

        augmented_data = pd.concat(augmented_rows)
        df_augmented = pd.concat([df, augmented_data]).reset_index(drop=True)
        return df_augmented

    def _clean_column(
        self,
        column,
        str_replace_special=False,
        lower=False,
        as_type_str=False,
        str_replace_comma=False,
        as_type_float=False,
    ):
        if str_replace_special:
            column = column.str.replace(
                r"[^\w\s]", "", regex=True
            )  # Remove special characters
        if lower:
            column = column.str.lower()  # Standardize text
        if as_type_str:
            column = column.astype(str)
        if (str_replace_comma) & (column.dtype == "O"):
            column = column.str.replace(",", "")
        if as_type_float:
            column = column.astype(float)

        return column
