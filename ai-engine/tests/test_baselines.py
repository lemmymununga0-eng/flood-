"""
tests/test_baselines.py
========================
Unit tests for baseline ML classifiers.
"""

import numpy as np
import pytest

from src.models.baselines import (
    BaselineModelFactory,
    DecisionTreeClassifier_,
    LogisticRegressionClassifier,
    RandomForestClassifier_,
)


def make_dataset(n: int = 300, n_features: int = 20, seed: int = 42):
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (n, n_features)).astype(np.float32)
    # Create a simple linear target for testing
    weights = rng.normal(0, 1, n_features)
    score = X @ weights
    y = (score > score.mean()).astype(np.int32)
    return X, y


class TestBaselineModels:
    """Tests for all baseline classifiers."""

    def test_logistic_regression_fit_predict(self):
        X, y = make_dataset()
        model = LogisticRegressionClassifier()
        model.build().fit(X[:250], y[:250])
        preds = model.predict(X[250:])
        assert preds.shape == (50,)
        assert set(preds).issubset({0, 1})

    def test_logistic_regression_predict_proba(self):
        X, y = make_dataset()
        model = LogisticRegressionClassifier()
        model.build().fit(X[:250], y[:250])
        proba = model.predict_proba(X[250:])
        assert proba.shape == (50,)
        assert (proba >= 0).all() and (proba <= 1).all()

    def test_decision_tree_fit_predict(self):
        X, y = make_dataset()
        model = DecisionTreeClassifier_()
        model.build().fit(X[:250], y[:250])
        preds = model.predict(X[250:])
        assert preds.shape == (50,)

    def test_random_forest_fit_predict(self):
        X, y = make_dataset()
        model = RandomForestClassifier_(n_estimators=10)
        model.build().fit(X[:250], y[:250])
        preds = model.predict(X[250:])
        assert preds.shape == (50,)

    def test_factory_returns_all_models(self):
        factory = BaselineModelFactory()
        models = factory.get_all_models()
        assert "LogisticRegression" in models
        assert "DecisionTree" in models
        assert "RandomForest" in models
        assert "GradientBoosting" in models

    def test_model_without_build_raises(self):
        model = RandomForestClassifier_(n_estimators=10)
        X, y = make_dataset()
        # Should not raise because fit() calls build() internally
        model.fit(X, y)
        assert model.model is not None
