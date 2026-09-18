"""
training/train_baselines.py
============================
Training runner for all baseline ML classifiers.

This module orchestrates the training loop for every baseline model:
  - Receives train/val/test splits
  - Trains each model
  - Logs metrics to the experiment tracker
  - Saves each trained model to disk
  - Returns a summary comparison table

Design decisions
----------------
- Each model is trained independently so a failure in one doesn't
  abort the others.
- Models are persisted with joblib (scikit-learn's recommended serialiser).
- The experiment tracker records every run with a versioned directory.

Usage
-----
    from src.training.train_baselines import BaselineTrainer
    from src.datasets.split_data import DataSplits

    trainer = BaselineTrainer()
    results = trainer.train_all(splits)
    print(results.to_string())
"""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.config.settings import settings
from src.datasets.split_data import DataSplits
from src.evaluation.metrics import ModelEvaluator
from src.models.baselines import BaselineModelFactory
from src.utils.experiment_tracker import ExperimentTracker
from src.utils.logger import get_logger
from src.utils.reproducibility import set_global_seed

logger = get_logger(__name__)


class BaselineTrainer:
    """
    Trains and evaluates all baseline classifiers.

    Parameters
    ----------
    save_dir : Path
        Directory to save trained model files.
    """

    def __init__(self, save_dir: Path = settings.saved_models_dir) -> None:
        self._save_dir = save_dir
        self._evaluator = ModelEvaluator()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def train_all(self, splits: DataSplits) -> pd.DataFrame:
        """
        Train all baseline classifiers and return a comparison table.

        Parameters
        ----------
        splits : DataSplits
            Pre-built train/val/test splits from DataSplitter.

        Returns
        -------
        pd.DataFrame
            Model comparison table with metrics for each classifier.
        """
        set_global_seed(settings.training.random_seed)
        factory = BaselineModelFactory()
        all_models = factory.get_all_models()

        results: list[dict[str, Any]] = []

        for model_name, classifier in all_models.items():
            logger.info(f"{'='*50}")
            logger.info(f"Training: {model_name}")
            logger.info(f"{'='*50}")

            tracker = ExperimentTracker(model_name=model_name)
            tracker.log_params(
                {
                    "model": model_name,
                    "n_train": len(splits.X_train),
                    "n_val": len(splits.X_val),
                    "n_test": len(splits.X_test),
                    "n_features": splits.X_train.shape[1],
                    "seed": settings.training.random_seed,
                }
            )

            try:
                # Train on train + val combined for final evaluation
                X_train_full = np.vstack([splits.X_train, splits.X_val])
                y_train_full = np.concatenate([splits.y_train, splits.y_val])
                classifier.build().fit(X_train_full, y_train_full)

                # Evaluate on test set
                y_pred = classifier.predict(splits.X_test)
                y_proba = self._safe_proba(classifier, splits.X_test)
                metrics = self._evaluator.compute_metrics(
                    y_true=splits.y_test,
                    y_pred=y_pred,
                    y_proba=y_proba,
                    model_name=model_name,
                )

                tracker.log_metrics(metrics)
                tracker.save()

                # Save model to disk
                model_path = self._save_dir / f"{model_name.lower()}_model.joblib"
                joblib.dump(classifier.model, model_path)
                logger.info(f"Model saved to {model_path}")

                metrics["model"] = model_name
                results.append(metrics)
                logger.info(f"{model_name} | F1={metrics['f1']:.4f} | ROC-AUC={metrics['roc_auc']:.4f}")

            except Exception as exc:
                logger.error(f"Failed to train {model_name}: {exc}")
                results.append({"model": model_name, "error": str(exc)})

        comparison = pd.DataFrame(results).set_index("model")
        comparison = comparison.sort_values("f1", ascending=False)

        # Save comparison table
        comparison_path = settings.reports_dir / "baseline_comparison.csv"
        comparison.to_csv(comparison_path)
        logger.info(f"Comparison table saved to {comparison_path}")
        logger.info(f"\n{comparison.to_string()}")

        return comparison

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safe_proba(
        self, classifier, X: np.ndarray
    ) -> np.ndarray | None:
        """Return probability estimates, or None if not supported."""
        try:
            return classifier.predict_proba(X)
        except (NotImplementedError, AttributeError):
            return None
