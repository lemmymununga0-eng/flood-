"""Phases 12, 15, 16, 21 - model selection, calibration, threshold, artifact export.

THE TEST SET IS NOT READ BY THIS SCRIPT.

Selection criterion, declared here in code before any result is inspected, so that the
choice cannot be retrofitted to whatever looked best:

  PRIMARY    validation PR-AUC. At a base rate near 0.1% the precision-recall curve is
             the informative one; ROC-AUC is dominated by the enormous true-negative
             mass and a model can score 0.78 there while being useless.
  GATE 1     the candidate must beat the best non-ML baseline's validation PR-AUC.
             A model that cannot outperform a day-of-year climatology has not earned
             the name "prediction".
  GATE 2     validation recall >= 0.30. A flood model that finds almost nothing is not
             preferable merely for ranking well.
  TIE-BREAK  fewer features, then the simpler model family. Applied only within 5%
             relative PR-AUC, because differences below that are noise at this many
             positives.

If no candidate passes the gates, this script says so and exports nothing. That is a
real possible outcome and it is not worked around.

Threshold objective (Phase 16), also declared up front: an alert is only useful if a
human can act on it, so the operating point is the one that maximises recall subject to
an alert budget of at most ALERTS_PER_LOCATION_PER_YEAR. Swept on validation only.

    python ml/pipeline/p15_finalize.py
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.frozen import FrozenEstimator  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402
from sklearn.preprocessing import RobustScaler  # noqa: E402
from sklearn.utils.class_weight import compute_sample_weight  # noqa: E402

from ml import config as C  # noqa: E402
from ml.pipeline.p10_experiments import (  # noqa: E402
    FEATURE_SETS, baseline_scores, evaluate, load, make_models, usable,
)

MIN_RECALL_GATE = 0.30
PR_AUC_TIE_BAND = 0.05
ALERTS_PER_LOCATION_PER_YEAR = 6.0   # a wet-season-scale budget a district office could act on
ARTIFACT_VERSION = "flood_risk_v2_corrected"


# ---------------------------------------------------------------------------

def select_candidate(abl: pd.DataFrame) -> tuple[dict, dict]:
    """Apply the declared criterion to the validation ablation table."""
    base = abl[abl.kind == "baseline"].dropna(subset=["pr_auc"])
    best_base = base.loc[base.pr_auc.idxmax()].to_dict()

    models = abl[(abl.kind == "model")].dropna(subset=["pr_auc"]).copy()
    passed = models[(models.pr_auc > best_base["pr_auc"]) & (models.recall >= MIN_RECALL_GATE)]

    print(f"\nBest non-ML baseline : {best_base['name']} "
          f"PR-AUC={best_base['pr_auc']:.6f} ROC-AUC={best_base['roc_auc']:.4f}")
    print(f"Candidates passing both gates: {len(passed)} of {len(models)}")

    if passed.empty:
        return {}, best_base

    top = passed.pr_auc.max()
    band = passed[passed.pr_auc >= top * (1 - PR_AUC_TIE_BAND)].copy()
    simplicity = {"LogisticRegression": 0, "DecisionTree": 1, "GradientBoosting": 2,
                  "RandomForest": 3, "XGBoost": 4}
    band["_simpler"] = band.name.map(simplicity).fillna(9)
    band = band.sort_values(["n_features", "_simpler", "pr_auc"],
                            ascending=[True, True, False])
    chosen = band.iloc[0].to_dict()
    print(f"Within the {PR_AUC_TIE_BAND:.0%} PR-AUC tie band: {len(band)} candidate(s); "
          f"chose the simplest.")
    return chosen, best_base


def fit_model(name: str, X, y):
    model = make_models()[name]
    if name == "XGBoost":
        neg, pos = (y == 0).sum(), (y == 1).sum()
        model.set_params(scale_pos_weight=neg / max(pos, 1))
        model.fit(X, y)
    elif name == "GradientBoosting":
        model.fit(X, y, sample_weight=compute_sample_weight("balanced", y))
    else:
        model.fit(X, y)
    return model


def choose_threshold(proba: np.ndarray, y: np.ndarray, n_locations: int,
                     n_days: int) -> dict:
    """Maximise recall subject to the declared alert budget. Validation only."""
    years = max(n_days / 365.25, 1e-9)
    budget_alerts = ALERTS_PER_LOCATION_PER_YEAR * n_locations * years

    rows = []
    for t in np.round(np.arange(0.01, 1.00, 0.01), 2):
        pred = (proba >= t).astype(int)
        m = evaluate(y, pred, proba)
        alerts = int(pred.sum())
        rows.append({"threshold": float(t), "alerts": alerts,
                     "alerts_per_location_per_year": alerts / n_locations / years,
                     "recall": m["recall"], "precision": m["precision"],
                     "f1": m["f1"], "tp": m["tp"], "fp": m["fp"], "fn": m["fn"]})
    sweep = pd.DataFrame(rows)
    sweep.to_csv(C.REPORTS_DIR / "threshold_sweep_validation.csv", index=False)

    affordable = sweep[sweep.alerts <= budget_alerts]
    if affordable.empty or affordable.recall.max() == 0:
        # Honest fallback: no threshold meets the budget with any recall at all.
        fallback = sweep.loc[sweep.f1.idxmax()]
        return {
            "threshold": float(fallback.threshold),
            "selected_by": "max validation F1 (fallback)",
            "budget_met": False,
            "budget_alerts_per_location_per_year": ALERTS_PER_LOCATION_PER_YEAR,
            "achieved_alerts_per_location_per_year": float(
                fallback.alerts_per_location_per_year),
            "validation_recall": float(fallback.recall),
            "validation_precision": float(fallback.precision),
            "note": (
                "NO threshold satisfies the stated alert budget while retaining non-zero "
                "recall. The budget-constrained objective is therefore unachievable for "
                "this model on this data, and the reported operating point is a max-F1 "
                "fallback rather than an operationally defensible one."
            ),
        }
    best = affordable.loc[affordable.recall.idxmax()]
    return {
        "threshold": float(best.threshold),
        "selected_by": (
            f"maximum validation recall subject to <= "
            f"{ALERTS_PER_LOCATION_PER_YEAR} alerts per location per year"),
        "budget_met": True,
        "budget_alerts_per_location_per_year": ALERTS_PER_LOCATION_PER_YEAR,
        "achieved_alerts_per_location_per_year": float(best.alerts_per_location_per_year),
        "validation_recall": float(best.recall),
        "validation_precision": float(best.precision),
        "validation_tp": int(best.tp), "validation_fp": int(best.fp),
        "validation_fn": int(best.fn),
    }


def main() -> None:
    C.ensure_out_dirs()
    abl_path = C.REPORTS_DIR / "validation_ablation.csv"
    if not abl_path.exists():
        raise SystemExit(f"missing {abl_path}; run ml/pipeline/p10_experiments.py first")

    train, val = usable(load("train")), usable(load("validation"))
    abl = pd.read_csv(abl_path)
    chosen, best_base = select_candidate(abl)

    if not chosen:
        verdict = {
            "outcome": "NO_MODEL_SELECTED",
            "reason": (
                "No model passed both declared gates: beat the best non-ML baseline's "
                "validation PR-AUC, and reach validation recall >= "
                f"{MIN_RECALL_GATE}. The honest conclusion is that on this data no "
                "machine-learning model demonstrates incremental skill over seasonality "
                "and rainfall accumulation."
            ),
            "best_baseline": {k: best_base[k] for k in ("name", "roc_auc", "pr_auc", "recall")},
            "gates": {"min_recall": MIN_RECALL_GATE, "must_beat_baseline_pr_auc": True},
        }
        (C.REPORTS_DIR / "selection_verdict.json").write_text(
            json.dumps(verdict, indent=2), encoding="utf-8")
        print("\n" + "=" * 72)
        print("NO MODEL SELECTED — see reports/selection_verdict.json")
        print(verdict["reason"])
        print("=" * 72)
        return

    mname, exp = chosen["name"], chosen["features"]
    feats = FEATURE_SETS[exp]
    print(f"\nSELECTED: {mname} / {exp} ({len(feats)} features)")
    print(f"  validation PR-AUC={chosen['pr_auc']:.6f} ROC-AUC={chosen['roc_auc']:.4f} "
          f"recall={chosen['recall']:.3f}")

    Xtr, ytr = train[feats].to_numpy(float), train[C.TARGET].to_numpy()
    Xva, yva = val[feats].to_numpy(float), val[C.TARGET].to_numpy()
    scaler = RobustScaler().fit(Xtr)
    model = fit_model(mname, scaler.transform(Xtr), ytr)

    # ---- Phase 15: calibration on VALIDATION only, against the frozen model ----
    Xva_s = scaler.transform(Xva)
    raw_val = model.predict_proba(Xva_s)[:, 1]
    calibrator = CalibratedClassifierCV(
        FrozenEstimator(model), method="sigmoid").fit(Xva_s, yva)
    cal_val = calibrator.predict_proba(Xva_s)[:, 1]

    calib = {
        "method": "sigmoid (Platt)",
        "fit_on": f"validation split only ({val.date.min().date()} to {val.date.max().date()})",
        "fit_rows": int(len(val)), "fit_positives": int(yva.sum()),
        "brier_raw": float(brier_score_loss(yva, raw_val)),
        "brier_calibrated": float(brier_score_loss(yva, cal_val)),
        "roc_auc_raw": float(roc_auc_score(yva, raw_val)),
        "roc_auc_calibrated": float(roc_auc_score(yva, cal_val)),
        "monotonic_remap": bool(
            abs(roc_auc_score(yva, raw_val) - roc_auc_score(yva, cal_val)) < 1e-6),
        "what_this_licenses": (
            "Calibrated outputs are monotonically ordered and correctly scaled to the "
            "base rate. With this few positives they support relative risk ranking, not "
            "a statement that probability p means a p chance of flooding."
        ),
    }
    print(f"  calibration: Brier {calib['brier_raw']:.5f} -> {calib['brier_calibrated']:.6f}, "
          f"ROC-AUC unchanged={calib['monotonic_remap']}")

    # ---- Phase 16: threshold on VALIDATION only ----
    thr = choose_threshold(raw_val, yva, n_locations=val.location.nunique(),
                           n_days=int((val.date.max() - val.date.min()).days) + 1)
    print(f"  threshold: {thr['threshold']} ({thr['selected_by']})")
    print(f"    budget met={thr['budget_met']} recall={thr['validation_recall']:.3f} "
          f"precision={thr['validation_precision']:.5f} "
          f"alerts/loc/yr={thr['achieved_alerts_per_location_per_year']:.2f}")

    # ---- Risk bands from validation percentiles of the CALIBRATED score ----
    bands = {
        "MODERATE": float(np.quantile(cal_val, 0.90)),
        "HIGH": float(np.quantile(cal_val, 0.99)),
        "CRITICAL": float(np.quantile(cal_val, 0.999)),
        "basis": "validation-split percentiles (p90 / p99 / p99.9) of the calibrated score",
        "meaning": "RELATIVE risk ranking, not an absolute probability of flooding",
    }

    # ---- Phase 21: artifact package ----
    out = C.ARTIFACT_DIR / ARTIFACT_VERSION
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / "model.joblib")
    joblib.dump(scaler, out / "scaler.joblib")
    joblib.dump(calibrator, out / "calibrator.joblib")
    (out / "feature_columns.json").write_text(json.dumps(feats, indent=2), encoding="utf-8")
    (out / "threshold_metadata.json").write_text(json.dumps(thr, indent=2), encoding="utf-8")
    (out / "calibration_metadata.json").write_text(json.dumps(calib, indent=2), encoding="utf-8")
    (out / "risk_bands.json").write_text(json.dumps(bands, indent=2), encoding="utf-8")

    training_meta = {
        "artifact_version": ARTIFACT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": mname,
        "feature_set": exp,
        "features": feats,
        "n_features": len(feats),
        "target": {
            "column": C.TARGET,
            "definition": f"a documented flood event occurs at the location within (t, t+{C.HORIZON_DAYS}]",
            "horizon_days": C.HORIZON_DAYS,
            "label_sources": ["DesInventar (UNDRR)", "Dartmouth Flood Observatory",
                              "Curated log: DMMU/WARMA/ReliefWeb/FloodList/Intl Charter"],
            "third_state": "label_usable=0 rows are excluded from training and evaluation",
        },
        "training_period": [str(train.date.min().date()), str(train.date.max().date())],
        "validation_period": [str(val.date.min().date()), str(val.date.max().date())],
        "test_period": "LOCKED - see p20_final_evaluation.py; evaluated once, after freeze",
        "rows": {"train_usable": int(len(train)), "validation_usable": int(len(val)),
                 "train_positives": int(ytr.sum()), "validation_positives": int(yva.sum())},
        "preprocessing": {"scaler": "RobustScaler", "fitted_on": "training split only",
                          "imputation": "none"},
        "class_imbalance": "class_weight/sample_weight only; no resampling of any split",
        "selection": {
            "primary_metric": "validation PR-AUC",
            "gate_beat_baseline": {"baseline": best_base["name"],
                                   "baseline_pr_auc": float(best_base["pr_auc"])},
            "gate_min_recall": MIN_RECALL_GATE,
            "tie_break": "fewest features, then simpler family, within 5% relative PR-AUC",
            "test_set_used_for_selection": False,
        },
        "dataset_version": "corrected-1.0.0",
        "feature_contract_version": "1.0.0",
        "seed": C.SEED,
        "provenance_note": (
            "The predecessor artifact flood_risk_lr_v1 was selected using test-split "
            "ROC-AUC. That contamination is recorded in ml/baseline/baseline_manifest.json "
            "and is not repeated here."
        ),
    }
    (out / "training_metadata.json").write_text(json.dumps(training_meta, indent=2),
                                                encoding="utf-8")
    (out / "model_metadata.json").write_text(json.dumps({
        "version": ARTIFACT_VERSION, "model_type": mname,
        "features": feats, "target": C.TARGET,
        "decision_threshold": thr["threshold"],
        "calibration_method": calib["method"],
        "risk_bands": {k: v for k, v in bands.items() if k in ("MODERATE", "HIGH", "CRITICAL")},
    }, indent=2), encoding="utf-8")

    print(f"\nArtifact written to {out}")
    for f in sorted(out.glob("*")):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
