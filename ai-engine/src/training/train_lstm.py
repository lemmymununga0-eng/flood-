"""
training/train_lstm.py
=======================
Training runner for the LSTM deep learning model.

This module orchestrates the LSTM training loop:
  - Sets reproducibility seeds
  - Builds the LSTM from ``src/models/lstm.py``
  - Trains with early stopping, LR scheduling, and checkpointing
  - Evaluates on the test set
  - Logs to the experiment tracker
  - Saves the model, training history, and evaluation plots

Design decisions
----------------
- We train on the training set only and validate on the val set during
  fitting.  The test set is never touched until final evaluation.
- Training history (loss, accuracy per epoch) is saved as a JSON so it
  can be plotted later.
- The LSTM training runner is separate from the baselines runner because
  LSTM training requires sequence (3D) inputs, not flat (2D) inputs.

Usage
-----
    from src.training.train_lstm import LSTMTrainer
    trainer = LSTMTrainer(n_features=45)
    trainer.train(splits)
"""

import json
from pathlib import Path

import numpy as np

from src.config.settings import settings
from src.datasets.split_data import DataSplits
from src.evaluation.metrics import ModelEvaluator
from src.models.lstm import LSTMFloodModel
from src.utils.experiment_tracker import ExperimentTracker
from src.utils.logger import get_logger
from src.utils.reproducibility import set_global_seed

logger = get_logger(__name__)


class LSTMTrainer:
    """
    Orchestrates LSTM model training and evaluation.

    Parameters
    ----------
    n_features : int
        Number of input features per time step.
    save_dir : Path
        Directory to save model weights and training artifacts.
    bidirectional : bool
        Whether to use Bidirectional LSTM layers.
    """

    def __init__(
        self,
        n_features: int,
        save_dir: Path = settings.saved_models_dir,
        bidirectional: bool = False,
    ) -> None:
        self.n_features = n_features
        self.save_dir = save_dir
        self.bidirectional = bidirectional
        self._evaluator = ModelEvaluator()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def train(self, splits: DataSplits) -> dict:
        """
        Train the LSTM model and evaluate on the test set.

        Parameters
        ----------
        splits : DataSplits
            Must have X_seq_train, X_seq_val, X_seq_test and corresponding
            y_seq arrays set (produced by FeatureEngineer.create_sequences).

        Returns
        -------
        dict
            Evaluation metrics on the test set.
        """
        set_global_seed(settings.training.random_seed)

        if splits.X_seq_train is None:
            raise ValueError(
                "DataSplits does not contain sequence arrays. "
                "Run FeatureEngineer.create_sequences() and "
                "DataSplitter.split_sequences() first."
            )

        tracker = ExperimentTracker(model_name="LSTM")
        tracker.log_params(
            {
                "model": "LSTM",
                "n_features": self.n_features,
                "window_size": settings.features.window_size,
                "lstm_units": settings.training.lstm_units,
                "dropout": settings.training.lstm_dropout,
                "learning_rate": settings.training.lstm_learning_rate,
                "epochs": settings.training.lstm_epochs,
                "batch_size": settings.training.lstm_batch_size,
                "patience": settings.training.lstm_patience,
                "bidirectional": self.bidirectional,
                "seed": settings.training.random_seed,
                "n_train_seq": len(splits.X_seq_train),
                "n_val_seq": len(splits.X_seq_val),
                "n_test_seq": len(splits.X_seq_test),
            }
        )

        try:
            # Build and train
            model = LSTMFloodModel(
                n_features=self.n_features,
                bidirectional=self.bidirectional,
            )
            model.build().train(
                X_train=splits.X_seq_train,
                y_train=splits.y_seq_train,
                X_val=splits.X_seq_val,
                y_val=splits.y_seq_val,
            )

            # Save model
            model.save(self.save_dir)

            # Save training history
            if model.history is not None:
                history_path = self.save_dir / "lstm_training_history.json"
                history_path.write_text(
                    json.dumps(
                        {k: [float(v) for v in vals]
                         for k, vals in model.history.history.items()},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                logger.info(f"Training history saved to {history_path}")

            # Evaluate on test set
            y_proba = model.predict_proba(splits.X_seq_test)
            y_pred = (y_proba >= 0.5).astype(int)
            metrics = self._evaluator.compute_metrics(
                y_true=splits.y_seq_test,
                y_pred=y_pred,
                y_proba=y_proba,
                model_name="LSTM",
            )

            tracker.log_metrics(metrics)
            tracker.save()

            logger.info(
                f"LSTM Test Results | F1={metrics['f1']:.4f} | "
                f"ROC-AUC={metrics['roc_auc']:.4f} | "
                f"Recall={metrics['recall']:.4f}"
            )
            return metrics

        except ImportError as exc:
            logger.error(
                f"Cannot train LSTM: {exc}\n"
                "TensorFlow requires Python 3.11. "
                "See docs/installation.md for setup instructions."
            )
            return {}
        except Exception as exc:
            logger.error(f"LSTM training failed: {exc}")
            raise
