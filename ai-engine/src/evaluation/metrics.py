"""
evaluation/metrics.py
======================
Evaluation metrics, curves, and reporting for FloodShield-Zambia.

Why these specific metrics?
----------------------------
Flood prediction is a safety-critical, class-imbalanced problem.

- **Accuracy** is MISLEADING here: if floods occur 5% of the time, a model
  that always predicts "No Flood" achieves 95% accuracy but is useless.

- **Recall** (sensitivity) is critical: we want to catch every real flood.
  A missed flood warning is more dangerous than a false alarm.

- **Precision** tells us how many of our flood warnings were real.

- **F1 Score** balances Precision and Recall into a single number.

- **ROC-AUC** measures the model's ability to rank flood days above normal
  days across ALL possible thresholds.

- **PR-AUC** (Precision-Recall AUC) is more informative than ROC-AUC for
  imbalanced datasets.

- **Brier Score** measures the quality of the probability calibration
  (how well the model's confidence matches its accuracy).

Usage
-----
    from src.evaluation.metrics import ModelEvaluator
    evaluator = ModelEvaluator()
    metrics = evaluator.compute_metrics(y_true, y_pred, y_proba, "RandomForest")
    evaluator.plot_confusion_matrix(y_true, y_pred, "RandomForest")
    evaluator.plot_roc_curve(y_true, y_proba, "RandomForest")
    evaluator.plot_pr_curve(y_true, y_proba, "RandomForest")
"""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.dpi": 120,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


class ModelEvaluator:
    """
    Computes evaluation metrics and generates diagnostic plots.

    Parameters
    ----------
    figures_dir : Path
        Directory where plots are saved.
    """

    def __init__(self, figures_dir: Path = settings.figures_dir) -> None:
        self._figures_dir = figures_dir

    # ------------------------------------------------------------------
    # Metrics computation
    # ------------------------------------------------------------------

    def compute_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        model_name: str = "Model",
    ) -> dict:
        """
        Compute a full suite of classification metrics.

        Parameters
        ----------
        y_true : np.ndarray
            Ground truth binary labels.
        y_pred : np.ndarray
            Binary predictions (0 or 1).
        y_proba : np.ndarray, optional
            Predicted probabilities for the positive class.
        model_name : str
            Label used for logging.

        Returns
        -------
        dict
            Dictionary of metric names to float values.
        """
        metrics: dict = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        }

        if y_proba is not None:
            try:
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
                metrics["pr_auc"] = float(average_precision_score(y_true, y_proba))
                metrics["brier_score"] = float(brier_score_loss(y_true, y_proba))
            except ValueError as exc:
                logger.warning(f"Could not compute probability metrics: {exc}")
                metrics["roc_auc"] = 0.0
                metrics["pr_auc"] = 0.0
                metrics["brier_score"] = 1.0
        else:
            metrics["roc_auc"] = 0.0
            metrics["pr_auc"] = 0.0
            metrics["brier_score"] = 1.0

        logger.info(
            f"\n{'='*50}\n{model_name} Test Metrics\n{'='*50}\n"
            + "\n".join(f"  {k}: {v:.4f}" for k, v in metrics.items())
            + f"\n\nClassification Report:\n"
            + classification_report(
                y_true, y_pred,
                target_names=["No Flood", "Flood"],
                zero_division=0,
            )
        )
        return metrics

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------

    def plot_confusion_matrix(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "Model",
        save: bool = True,
    ) -> plt.Figure:
        """
        Plot and optionally save a confusion matrix.

        The confusion matrix shows how many flood/no-flood days were
        correctly and incorrectly classified.

        Parameters
        ----------
        y_true : np.ndarray
        y_pred : np.ndarray
        model_name : str
        save : bool

        Returns
        -------
        matplotlib.figure.Figure
        """
        cm = confusion_matrix(y_true, y_pred)
        fig, ax = plt.subplots(figsize=(6, 5))
        disp = ConfusionMatrixDisplay(
            confusion_matrix=cm,
            display_labels=["No Flood", "Flood"],
        )
        disp.plot(ax=ax, cmap="Blues", colorbar=False)
        ax.set_title(f"Confusion Matrix — {model_name}", fontsize=14, pad=12)
        fig.tight_layout()

        if save:
            path = self._figures_dir / f"confusion_matrix_{model_name.lower()}.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Confusion matrix saved to {path}")

        return fig

    def plot_roc_curve(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        model_name: str = "Model",
        save: bool = True,
    ) -> plt.Figure:
        """
        Plot the ROC (Receiver Operating Characteristic) curve.

        The ROC curve shows the trade-off between True Positive Rate (recall)
        and False Positive Rate at every decision threshold.  The AUC (Area
        Under the Curve) summarises this into a single score.  AUC = 0.5 is
        random; AUC = 1.0 is perfect.

        Parameters
        ----------
        y_true : np.ndarray
        y_proba : np.ndarray
        model_name : str
        save : bool

        Returns
        -------
        matplotlib.figure.Figure
        """
        fpr, tpr, _ = roc_curve(y_true, y_proba)
        auc = roc_auc_score(y_true, y_proba)

        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(fpr, tpr, color="#2563EB", lw=2, label=f"ROC AUC = {auc:.4f}")
        ax.plot([0, 1], [0, 1], "k--", lw=1, label="Random classifier")
        ax.fill_between(fpr, tpr, alpha=0.08, color="#2563EB")
        ax.set_xlabel("False Positive Rate", fontsize=12)
        ax.set_ylabel("True Positive Rate (Recall)", fontsize=12)
        ax.set_title(f"ROC Curve — {model_name}", fontsize=14, pad=12)
        ax.legend(loc="lower right", fontsize=11)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.02])
        fig.tight_layout()

        if save:
            path = self._figures_dir / f"roc_curve_{model_name.lower()}.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"ROC curve saved to {path}")

        return fig

    def plot_pr_curve(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        model_name: str = "Model",
        save: bool = True,
    ) -> plt.Figure:
        """
        Plot the Precision-Recall curve.

        For imbalanced datasets, the Precision-Recall curve is more
        informative than the ROC curve.  It focuses on the positive class
        (Flood days) without being skewed by the large number of normal days.

        Parameters
        ----------
        y_true : np.ndarray
        y_proba : np.ndarray
        model_name : str
        save : bool

        Returns
        -------
        matplotlib.figure.Figure
        """
        precision, recall, _ = precision_recall_curve(y_true, y_proba)
        pr_auc = average_precision_score(y_true, y_proba)
        baseline = y_true.mean()

        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(recall, precision, color="#DC2626", lw=2,
                label=f"PR AUC = {pr_auc:.4f}")
        ax.axhline(y=baseline, color="k", linestyle="--", lw=1,
                   label=f"Baseline (flood rate = {baseline:.1%})")
        ax.fill_between(recall, precision, alpha=0.08, color="#DC2626")
        ax.set_xlabel("Recall", fontsize=12)
        ax.set_ylabel("Precision", fontsize=12)
        ax.set_title(f"Precision-Recall Curve — {model_name}", fontsize=14, pad=12)
        ax.legend(loc="upper right", fontsize=11)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.05])
        fig.tight_layout()

        if save:
            path = self._figures_dir / f"pr_curve_{model_name.lower()}.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"PR curve saved to {path}")

        return fig

    def plot_training_history(
        self,
        history_dict: dict,
        model_name: str = "LSTM",
        save: bool = True,
    ) -> plt.Figure:
        """
        Plot LSTM training and validation loss/AUC over epochs.

        This plot helps diagnose:
        - Overfitting: val_loss increases while train_loss decreases
        - Underfitting: both losses remain high
        - Good fit: both converge to similar low values

        Parameters
        ----------
        history_dict : dict
            Dictionary from model.history.history (Keras training History).
        model_name : str
        save : bool

        Returns
        -------
        matplotlib.figure.Figure
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Loss
        ax1.plot(history_dict.get("loss", []), label="Train Loss", color="#2563EB")
        ax1.plot(history_dict.get("val_loss", []), label="Val Loss",
                 color="#DC2626", linestyle="--")
        ax1.set_title(f"{model_name} — Training Loss", fontsize=13)
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Binary Cross-Entropy Loss")
        ax1.legend()

        # AUC
        ax2.plot(history_dict.get("auc", []), label="Train AUC", color="#059669")
        ax2.plot(history_dict.get("val_auc", []), label="Val AUC",
                 color="#D97706", linestyle="--")
        ax2.set_title(f"{model_name} — ROC AUC", fontsize=13)
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("AUC")
        ax2.legend()

        fig.suptitle(f"{model_name} Training History", fontsize=15, y=1.01)
        fig.tight_layout()

        if save:
            path = self._figures_dir / f"training_history_{model_name.lower()}.png"
            fig.savefig(path, bbox_inches="tight")
            logger.info(f"Training history plot saved to {path}")

        return fig

    def generate_full_report(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray],
        model_name: str,
    ) -> dict:
        """
        Run all evaluations and generate all plots for a single model.

        Parameters
        ----------
        y_true : np.ndarray
        y_pred : np.ndarray
        y_proba : np.ndarray or None
        model_name : str

        Returns
        -------
        dict
            All computed metrics.
        """
        metrics = self.compute_metrics(y_true, y_pred, y_proba, model_name)
        self.plot_confusion_matrix(y_true, y_pred, model_name)
        if y_proba is not None:
            self.plot_roc_curve(y_true, y_proba, model_name)
            self.plot_pr_curve(y_true, y_proba, model_name)
        return metrics
