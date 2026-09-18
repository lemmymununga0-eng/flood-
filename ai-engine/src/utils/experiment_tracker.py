"""
utils/experiment_tracker.py
============================
Lightweight experiment tracker for the FloodShield-Zambia AI Engine.

Why track experiments?
-----------------------
In machine learning research it is essential to record exactly what
hyperparameters, dataset version, and random seed produced a given result.
Without this, you cannot reproduce a good result or understand why one model
outperformed another.

This tracker writes structured JSON files to ``experiments/run_XXX/`` so
that every run is self-contained and comparable.

Usage
-----
    from src.utils.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker(model_name="RandomForest")
    tracker.log_params({"n_estimators": 200, "max_depth": 6})
    tracker.log_metrics({"f1": 0.87, "roc_auc": 0.92})
    tracker.save()
    print(tracker.run_dir)
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentTracker:
    """
    Tracks a single training experiment run.

    Each run creates a numbered directory under ``experiments/`` containing:
    - ``config.json``   — hyperparameters and metadata
    - ``metrics.json``  — evaluation results
    - ``artifacts/``    — plots and model artefacts copied here

    Parameters
    ----------
    model_name : str
        A short label for the model (e.g. "LSTM", "RandomForest").
    experiments_dir : Path, optional
        Base directory for experiments.  Defaults to ``settings.experiments_dir``.
    """

    def __init__(
        self,
        model_name: str,
        experiments_dir: Path = settings.experiments_dir,
    ) -> None:
        self.model_name = model_name
        self.experiments_dir = experiments_dir
        self.run_id: int = self._next_run_id()
        self.run_dir: Path = experiments_dir / f"run_{self.run_id:03d}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "artifacts").mkdir(exist_ok=True)

        self._params: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {}
        self._started_at: str = datetime.now(timezone.utc).isoformat()

        logger.info(f"Experiment tracker initialised: {self.run_dir}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_params(self, params: dict[str, Any]) -> None:
        """
        Record hyperparameters for this run.

        Parameters
        ----------
        params : dict
            Key-value pairs of hyperparameter names and values.
        """
        self._params.update(params)
        logger.debug(f"Logged params: {params}")

    def log_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Record evaluation metrics for this run.

        Parameters
        ----------
        metrics : dict
            Key-value pairs such as {"f1": 0.87, "roc_auc": 0.92}.
        """
        self._metrics.update(metrics)
        logger.debug(f"Logged metrics: {metrics}")

    def save_artifact(self, source_path: Path) -> None:
        """
        Copy a file (plot, model, etc.) into the run's artifacts directory.

        Parameters
        ----------
        source_path : Path
            Path to the file to copy.
        """
        dest = self.run_dir / "artifacts" / source_path.name
        shutil.copy2(source_path, dest)
        logger.debug(f"Artifact saved: {dest}")

    def save(self) -> None:
        """
        Persist the experiment metadata to JSON files.

        Writes ``config.json`` and ``metrics.json`` in the run directory.
        """
        config = {
            "run_id": self.run_id,
            "model_name": self.model_name,
            "started_at": self._started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "random_seed": settings.training.random_seed,
            "window_size": settings.features.window_size,
            "params": self._params,
        }
        metrics_out = {
            "run_id": self.run_id,
            "model_name": self.model_name,
            "metrics": self._metrics,
        }

        (self.run_dir / "config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        (self.run_dir / "metrics.json").write_text(
            json.dumps(metrics_out, indent=2), encoding="utf-8"
        )
        logger.info(f"Experiment saved to {self.run_dir}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _next_run_id(self) -> int:
        """Return the next available run ID by scanning existing run dirs."""
        existing = [
            int(p.name.split("_")[1])
            for p in self.experiments_dir.glob("run_*")
            if p.is_dir() and p.name.split("_")[1].isdigit()
        ]
        return max(existing, default=0) + 1
