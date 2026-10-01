#!/usr/bin/env python3
"""Register the real trained flood-risk model in the model_versions table.

Every value written here is a real, measured result from the research bundle's
chronological evaluation (see its docs/FINAL_MODEL_SELECTION.md) — no metric is
estimated, rounded up, or invented. Precision really is 0.0006; it is recorded as-is
because hiding it would misrepresent the model.

Idempotent: re-running updates the existing row rather than creating duplicates.

    python scripts/register_model.py
"""
import json
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.models.prediction import ModelVersion  # noqa: E402

VERSION = "flood_risk_lr_v1"

METRICS = {
    "model_type": "LogisticRegression",
    "feature_set": "Experiment A (weather-only, 6 features)",
    "features": ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"],
    "target": "flood_next_7d (flood occurring within the following 7 days)",
    "split": "chronological by date; test split is strictly future relative to train/validation",
    "test": {
        "roc_auc": 0.777,
        "pr_auc": 0.0014,
        "precision": 0.0006,
        "recall": 0.889,
        "f1": 0.0013,
        "true_positives": 56,
        "false_positives": 88184,
        "true_negatives": 75671,
        "false_negatives": 7,
        "positive_prevalence": 0.00038,
    },
    "validation": {"roc_auc": 0.601, "recall": 0.703},
    "calibration": {
        "method": "sigmoid (Platt)",
        "brier_raw": 0.2678,
        "brier_calibrated": 0.00039,
        "roc_auc_unchanged": True,
    },
    "decision_threshold": 0.5,
    # Real measured comparison of every model trained on the same chronological split
    # and identical weather-only feature set. Accuracy is included deliberately to show
    # why it is the wrong headline metric here: the best-ranking model (Logistic
    # Regression, ROC-AUC 0.777) has the LOWEST accuracy, because it accepts many false
    # alarms in order to catch 56 of 63 real events.
    "model_comparison": [
        {"model": "LogisticRegression", "accuracy": 0.4620, "precision": 0.0006,
         "recall": 0.8889, "f1": 0.0013, "roc_auc": 0.7772, "pr_auc": 0.0014,
         "tp": 56, "fp": 88184, "fn": 7, "selected": True},
        {"model": "RandomForest", "accuracy": 0.7855, "precision": 0.0009,
         "recall": 0.4921, "f1": 0.0018, "roc_auc": 0.6503, "pr_auc": 0.0009,
         "tp": 31, "fp": 35134, "fn": 32, "selected": False},
        {"model": "GradientBoosting", "accuracy": 0.5683, "precision": 0.0006,
         "recall": 0.6667, "f1": 0.0012, "roc_auc": 0.6488, "pr_auc": 0.0021,
         "tp": 42, "fp": 70744, "fn": 21, "selected": False},
        {"model": "XGBoost", "accuracy": 0.7294, "precision": 0.0007,
         "recall": 0.5079, "f1": 0.0014, "roc_auc": 0.6473, "pr_auc": 0.0009,
         "tp": 32, "fp": 44326, "fn": 31, "selected": False},
        {"model": "DecisionTree", "accuracy": 0.5740, "precision": 0.0005,
         "recall": 0.6032, "f1": 0.0011, "roc_auc": 0.6156, "pr_auc": 0.0009,
         "tp": 38, "fp": 69812, "fn": 25, "selected": False},
    ],
    "models_not_trained": [
        {"model": "LSTM", "reason": "TensorFlow is not installed on this Python 3.14 "
                                     "environment; no LSTM was ever trained, so no "
                                     "metrics are reported for it."},
    ],
    # Real SHAP global importance (mean |SHAP value|) for the selected model.
    "shap_global_importance": [
        {"feature": "RH2M", "mean_abs_shap": 0.8895},
        {"feature": "T2M_MAX", "mean_abs_shap": 0.8008},
        {"feature": "T2M", "mean_abs_shap": 0.6059},
        {"feature": "T2M_MIN", "mean_abs_shap": 0.2127},
        {"feature": "PRECTOTCORR", "mean_abs_shap": 0.0249},
        {"feature": "WS10M", "mean_abs_shap": 0.0127},
    ],
    "known_limitations": [
        "Precision is unusably low for operational alerting (~0.06%); this is a "
        "research-grade risk signal, not a deployable warning system.",
        "Trained on NASA POWER MERRA-2 reanalysis (model-derived), not direct station "
        "observation. No Zambian station reports humidity or wind to GHCN-Daily.",
        "Test metrics rest on only 63 positive examples and are correspondingly noisy.",
    ],
    # ---------------------------------------------------------------------------
    # Added 2026-09-30 after the corrected-pipeline study (see ml/ in the repo).
    # These supersede the headline reading of the metrics above. They are recorded on
    # the registered model itself so the UI cannot display the flattering number
    # without the finding that qualifies it.
    # ---------------------------------------------------------------------------
    "corrected_study_2026_09_30": {
        "what_changed": (
            "Labels reconciled across three documentary sources (DesInventar, Dartmouth "
            "Flood Observatory, and this project's own curated DMMU/WARMA/Charter log); "
            "year-precision events changed from silent NEGATIVES to an explicit "
            "excluded-from-both-classes state; weather coverage completed from 59 to all "
            "82 districts; model selection moved to validation only, with the test split "
            "locked."
        ),
        "selection_contamination_disclosed": (
            "The v1 model above was selected by citing its TEST ROC-AUC of 0.777. On the "
            "validation split a different model ranked first. That figure is therefore an "
            "in-sample result and must not be reported as out-of-sample performance."
        ),
        "headline_finding": (
            "Across 25 runs (5 model families x 5 feature sets) on corrected labels, NO "
            "machine-learning model beat a day-of-year seasonal climatology baseline that "
            "uses no weather data at all."
        ),
        "validation_comparison": [
            {"name": "seasonal_climatology (no weather)", "kind": "baseline",
             "roc_auc": 0.6401, "pr_auc": 0.003363, "recall": 0.743, "rank": 1},
            {"name": "XGBoost + soil moisture", "kind": "model",
             "roc_auc": 0.6136, "pr_auc": 0.002998, "recall": 0.260, "rank": 2},
            {"name": "XGBoost + rainfall accumulation", "kind": "model",
             "roc_auc": 0.6414, "pr_auc": 0.002917, "recall": 0.248, "rank": 3},
            {"name": "LogisticRegression weather-only (this model)", "kind": "model",
             "roc_auc": 0.6041, "pr_auc": 0.002504, "recall": 0.695, "rank": 14},
        ],
        "selection_outcome": "NO_MODEL_SELECTED - 0 of 25 candidates passed the "
                             "pre-declared gates (beat the baseline's PR-AUC, and reach "
                             "recall >= 0.30).",
        "intended_use": (
            "Research and teaching only. This model must NOT be used to issue public or "
            "institutional flood warnings. It does not demonstrate predictive skill "
            "beyond knowing the time of year."
        ),
    },
}


def main() -> None:
    artifact_path = str(pathlib.Path("./ml_artifacts") / VERSION)
    db = SessionLocal()
    try:
        existing = db.scalar(select(ModelVersion).where(ModelVersion.version == VERSION))
        if existing is None:
            row = ModelVersion(
                version=VERSION,
                model_type="LogisticRegression",
                training_period_start=datetime(1990, 1, 1),
                training_period_end=datetime(2015, 7, 20),
                metrics_json=json.dumps(METRICS, indent=2),
                artifact_path=artifact_path,
                is_active=True,
            )
            db.add(row)
            action = "CREATED"
        else:
            existing.metrics_json = json.dumps(METRICS, indent=2)
            existing.artifact_path = artifact_path
            existing.is_active = True
            action = "UPDATED"
        db.commit()
        print(f"{action} model_versions row for {VERSION} (is_active=True)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
