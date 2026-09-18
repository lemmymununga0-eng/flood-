"""
models/baselines.py
====================
Classical Machine Learning baseline classifiers for FloodShield-Zambia.

Why do we train baseline models?
----------------------------------
Before deploying a complex deep learning model (LSTM), we must first
establish a performance baseline using simpler models.

The baseline serves three purposes:
  1. **Sanity check** — if the LSTM cannot beat Random Forest, something
     is wrong with the LSTM architecture or data preparation.
  2. **Interpretability** — simpler models are easier to explain to
     non-technical stakeholders (e.g. Zambia government agencies).
  3. **Deployment fallback** — if computational resources are limited,
     Random Forest can run on a Raspberry Pi while LSTM requires a GPU.

Models implemented
------------------
1. LogisticRegression  — Linear classifier, our minimum baseline
2. DecisionTree        — Non-linear but fully interpretable
3. RandomForest        — Ensemble of decision trees (strong performer)
4. GradientBoosting    — Sequential boosting ensemble (often best baseline)
5. XGBoost             — Optimised gradient boosting (industry standard)

Design decisions
----------------
- All models share a common ``BaseClassifier`` interface so training,
  evaluation, and saving are identical regardless of model type.
- Class imbalance is handled via ``class_weight="balanced"`` where
  supported (flood events are rare compared to normal days).
- Models are wrapped in scikit-learn Pipeline objects with no scaling
  (scaling was already done by FeatureEngineer).

Usage
-----
    from src.models.baselines import BaselineModelFactory
    factory = BaselineModelFactory()
    models = factory.get_all_models()
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Try to import XGBoost — it's optional
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not installed. Install with: pip install xgboost")


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------
class BaseFloodClassifier(ABC):
    """
    Abstract base class that all FloodShield classifiers must implement.

    This enforces a consistent interface across models so the training and
    evaluation pipelines don't need model-specific code.
    """

    def __init__(self, name: str, seed: int = settings.training.random_seed) -> None:
        self.name = name
        self.seed = seed
        self._model = None

    @abstractmethod
    def build(self) -> "BaseFloodClassifier":
        """Initialise and return the underlying sklearn estimator."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseFloodClassifier":
        """
        Train the model on training data.

        Parameters
        ----------
        X : np.ndarray of shape (n_samples, n_features)
        y : np.ndarray of shape (n_samples,)

        Returns
        -------
        self
        """
        if self._model is None:
            self.build()
        logger.info(f"Training {self.name} ...")
        self._model.fit(X, y)
        logger.info(f"{self.name} training complete ✓")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return class predictions (0 or 1)."""
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability estimates for each class."""
        if hasattr(self._model, "predict_proba"):
            return self._model.predict_proba(X)[:, 1]
        raise NotImplementedError(f"{self.name} does not support predict_proba")

    @property
    def model(self):
        """The underlying sklearn estimator."""
        return self._model


# ---------------------------------------------------------------------------
# Concrete classifiers
# ---------------------------------------------------------------------------
class LogisticRegressionClassifier(BaseFloodClassifier):
    """
    Logistic Regression — linear classifier.

    Why include it?
    ---------------
    Logistic Regression is the simplest possible classifier.  Any model that
    cannot beat this baseline has serious problems.  It also provides
    coefficient-based feature importance.
    """

    def __init__(self, seed: int = settings.training.random_seed) -> None:
        super().__init__("LogisticRegression", seed)

    def build(self) -> "LogisticRegressionClassifier":
        self._model = LogisticRegression(
            class_weight="balanced",  # Handles class imbalance
            max_iter=1000,            # More iterations for convergence
            random_state=self.seed,
            solver="lbfgs",
            C=1.0,                   # Regularisation strength (L2)
        )
        return self


class DecisionTreeClassifier_(BaseFloodClassifier):
    """
    Decision Tree — fully interpretable, no ensemble.

    Why include it?
    ---------------
    Decision Trees produce human-readable rules, e.g.:
    "IF 7-day rainfall > 75mm AND soil moisture > 0.8 THEN Flood"
    This kind of rule is very useful for explaining predictions to
    Zambia's Disaster Management and Mitigation Unit (DMMU).
    """

    def __init__(
        self,
        max_depth: int = settings.training.max_depth,
        seed: int = settings.training.random_seed,
    ) -> None:
        super().__init__("DecisionTree", seed)
        self.max_depth = max_depth

    def build(self) -> "DecisionTreeClassifier_":
        self._model = DecisionTreeClassifier(
            max_depth=self.max_depth,
            class_weight="balanced",
            random_state=self.seed,
            min_samples_split=20,
            min_samples_leaf=10,
        )
        return self


class RandomForestClassifier_(BaseFloodClassifier):
    """
    Random Forest — ensemble of decision trees.

    Why is this often the best baseline?
    --------------------------------------
    Random Forest averages predictions from many trees, reducing the
    high variance of a single decision tree.  It handles:
    - Non-linear relationships (unlike Logistic Regression)
    - Feature interactions automatically
    - Missing feature correlations via bootstrap sampling

    It is also fast to train and robust to hyperparameter choices.
    """

    def __init__(
        self,
        n_estimators: int = settings.training.n_estimators,
        max_depth: int = settings.training.max_depth,
        seed: int = settings.training.random_seed,
    ) -> None:
        super().__init__("RandomForest", seed)
        self.n_estimators = n_estimators
        self.max_depth = max_depth

    def build(self) -> "RandomForestClassifier_":
        self._model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            class_weight="balanced",
            random_state=self.seed,
            n_jobs=-1,               # Use all CPU cores
            min_samples_split=20,
            min_samples_leaf=10,
            max_features="sqrt",     # Random feature subsets for diversity
        )
        return self


class GradientBoostingClassifier_(BaseFloodClassifier):
    """
    Gradient Boosting — sequential boosting ensemble.

    How does it differ from Random Forest?
    ----------------------------------------
    Random Forest builds trees in parallel (bagging).
    Gradient Boosting builds trees sequentially — each new tree corrects the
    errors of the previous one.  This makes it more accurate on clean data
    but more prone to overfitting.
    """

    def __init__(
        self,
        n_estimators: int = settings.training.n_estimators,
        max_depth: int = settings.training.max_depth,
        seed: int = settings.training.random_seed,
    ) -> None:
        super().__init__("GradientBoosting", seed)
        self.n_estimators = n_estimators
        self.max_depth = max_depth

    def build(self) -> "GradientBoostingClassifier_":
        self._model = GradientBoostingClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=0.05,
            subsample=0.8,           # Row subsampling (reduces overfitting)
            min_samples_split=20,
            random_state=self.seed,
        )
        return self


class XGBoostClassifier_(BaseFloodClassifier):
    """
    XGBoost — industry-standard optimised gradient boosting.

    XGBoost extends Gradient Boosting with:
    - Regularisation (L1 and L2)
    - Parallel tree building
    - Handling of missing values natively
    - Sparsity-aware split finding
    """

    def __init__(
        self,
        n_estimators: int = settings.training.n_estimators,
        max_depth: int = settings.training.max_depth,
        seed: int = settings.training.random_seed,
    ) -> None:
        super().__init__("XGBoost", seed)
        self.n_estimators = n_estimators
        self.max_depth = max_depth

    def build(self) -> "XGBoostClassifier_":
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost is not installed. Run: pip install xgboost")
        self._model = XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=10,     # Handles class imbalance in XGBoost
            random_state=self.seed,
            eval_metric="logloss",
            verbosity=0,
        )
        return self


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
class BaselineModelFactory:
    """
    Factory class for creating all baseline models.

    Usage
    -----
    >>> factory = BaselineModelFactory()
    >>> models = factory.get_all_models()
    >>> for name, model in models.items():
    ...     model.build().fit(X_train, y_train)
    """

    def get_all_models(self) -> dict[str, BaseFloodClassifier]:
        """
        Return a dict of all available baseline models.

        Returns
        -------
        dict[str, BaseFloodClassifier]
            Keys are model names; values are classifier instances.
        """
        models: dict[str, BaseFloodClassifier] = {
            "LogisticRegression": LogisticRegressionClassifier(),
            "DecisionTree": DecisionTreeClassifier_(),
            "RandomForest": RandomForestClassifier_(),
            "GradientBoosting": GradientBoostingClassifier_(),
        }
        if XGBOOST_AVAILABLE:
            models["XGBoost"] = XGBoostClassifier_()
        else:
            logger.warning("XGBoost excluded from model suite (not installed).")
        return models
