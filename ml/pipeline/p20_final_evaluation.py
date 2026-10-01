"""Phases 18, 20, 23, 24 - the single locked-test evaluation, plus error analysis.

This is the ONLY script in the package that reads test.csv. It runs after the pipeline is
frozen by p15_finalize.py, and it runs once. It selects nothing, tunes nothing, and
changes nothing: the model, scaler, calibrator, threshold and risk bands are all loaded
from the frozen artifact exactly as produced.

It reports, separately and never mixed:
  * validation metrics (already seen during development)
  * locked-test metrics (seen once, here)
  * the reference baselines, computed on the same test split for a like-for-like read

and then the operationally meaningful figures the day-level confusion matrix hides:
  * EVENT-level detection - did any alert fire in the 7 days before a real event
  * lead time - how many days of warning each detected event got
  * alert burden - alerts per location per year
  * error analysis - where the false negatives and false positives sit

    python ml/pipeline/p20_final_evaluation.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402
from ml.pipeline.p10_experiments import baseline_scores, evaluate, load, usable  # noqa: E402
from ml.pipeline.p15_finalize import ARTIFACT_VERSION  # noqa: E402


def load_artifact() -> dict:
    root = C.ARTIFACT_DIR / ARTIFACT_VERSION
    if not root.exists():
        raise SystemExit(f"no frozen artifact at {root}; run ml/pipeline/p15_finalize.py")
    return {
        "model": joblib.load(root / "model.joblib"),
        "scaler": joblib.load(root / "scaler.joblib"),
        "calibrator": joblib.load(root / "calibrator.joblib"),
        "features": json.loads((root / "feature_columns.json").read_text()),
        "threshold": json.loads((root / "threshold_metadata.json").read_text()),
        "bands": json.loads((root / "risk_bands.json").read_text()),
        "training": json.loads((root / "training_metadata.json").read_text()),
    }


def event_level_detection(df: pd.DataFrame, alert: np.ndarray, horizon: int = 7) -> dict:
    """An event is detected when at least one alert fires on a day whose forecast window
    covers the event's onset. Lead time is measured from the earliest such alert.

    This is the figure a district officer cares about. Day-level precision is not."""
    d = df.copy()
    d["_alert"] = alert
    events, detected, leads = 0, 0, []

    for loc, g in d.groupby("location", sort=False):
        g = g.sort_values("date")
        onsets = g.loc[g["flood_reliable"] == 1, "date"] if "flood_reliable" in g else pd.Series([], dtype="datetime64[ns]")
        # Collapse consecutive flood days into single events.
        onset_list = []
        for dt in onsets:
            if not onset_list or (dt - onset_list[-1]).days > 1:
                onset_list.append(dt)
        for onset in onset_list:
            events += 1
            window = g[(g.date >= onset - pd.Timedelta(days=horizon)) &
                       (g.date <= onset - pd.Timedelta(days=1))]
            fired = window[window["_alert"] == 1]
            if len(fired):
                detected += 1
                leads.append(int((onset - fired.date.min()).days))

    return {
        "events": events, "detected": detected,
        "event_detection_rate": round(detected / events, 4) if events else float("nan"),
        "median_lead_days": float(np.median(leads)) if leads else float("nan"),
        "mean_lead_days": round(float(np.mean(leads)), 2) if leads else float("nan"),
        "lead_day_distribution": {str(k): int(v) for k, v in
                                  sorted(pd.Series(leads).value_counts().items())} if leads else {},
    }


def alert_burden(df: pd.DataFrame, alert: np.ndarray) -> dict:
    years = max(((df.date.max() - df.date.min()).days + 1) / 365.25, 1e-9)
    n_loc = df.location.nunique()
    total = int(alert.sum())
    return {
        "total_alerts": total,
        "alerts_per_location_per_year": round(total / n_loc / years, 2),
        "days_between_alerts_per_location": round(365.25 / max(total / n_loc / years, 1e-9), 1),
    }


def error_analysis(df: pd.DataFrame, proba: np.ndarray, alert: np.ndarray) -> dict:
    d = df.copy()
    d["_p"] = proba
    d["_alert"] = alert
    y = d[C.TARGET].to_numpy()

    fn = d[(y == 1) & (alert == 0)]
    fp = d[(y == 0) & (alert == 1)]
    tn = d[(y == 0) & (alert == 0)]

    def prof(part: pd.DataFrame) -> dict:
        if part.empty:
            return {}
        out = {"n": int(len(part))}
        for c in ("PRECTOTCORR", "rain_7day", "RH2M", "T2M_MAX"):
            if c in part.columns:
                out[f"mean_{c}"] = round(float(part[c].mean()), 3)
        return out

    return {
        "false_negatives": {
            **prof(fn),
            "by_location": {k: int(v) for k, v in fn.location.value_counts().head(10).items()},
            "by_month": {str(k): int(v) for k, v in fn.date.dt.month.value_counts().sort_index().items()},
        },
        "false_positives": {
            **prof(fp),
            "by_month": {str(k): int(v) for k, v in fp.date.dt.month.value_counts().sort_index().items()},
            "top_locations": {k: int(v) for k, v in fp.location.value_counts().head(10).items()},
        },
        "true_negatives_for_contrast": prof(tn),
        "interpretation_caveat": (
            "False positives cannot be interpreted as pure model error. The label is known "
            "to be incomplete: every one of the nine independently documented floods in "
            "the project's own curated log is a negative in the predecessor dataset, and "
            "1990-1997, 1999, 2018, 2019 and 2024 still contain no documented district-level "
            "events. Some false alarms are very likely unrecorded floods. None has been "
            "relabelled on that suspicion."
        ),
    }


def main() -> None:
    C.ensure_out_dirs()
    art = load_artifact()
    feats = art["features"]
    thr = art["threshold"]["threshold"]

    train = usable(load("train"))
    val = usable(load("validation"))
    test = usable(load("test"))

    print("=" * 74)
    print("LOCKED TEST EVALUATION - run once, on a frozen pipeline")
    print("=" * 74)
    print(f"artifact   : {ARTIFACT_VERSION}")
    print(f"model      : {art['training']['model_type']} / {art['training']['feature_set']}")
    print(f"threshold  : {thr}  ({art['threshold']['selected_by']})")
    print(f"test split : {test.date.min().date()} -> {test.date.max().date()}  "
          f"rows={len(test):,} positives={int(test[C.TARGET].sum())} "
          f"({test[C.TARGET].mean():.4%})\n")

    report: dict = {"artifact_version": ARTIFACT_VERSION,
                    "model": art["training"]["model_type"],
                    "feature_set": art["training"]["feature_set"],
                    "threshold": thr,
                    "splits": {}, "baselines": {}, "operational": {}, "errors": {}}

    for name, part in (("validation", val), ("test", test)):
        X = art["scaler"].transform(part[feats].to_numpy(float))
        raw = art["model"].predict_proba(X)[:, 1]
        cal = art["calibrator"].predict_proba(X)[:, 1]
        alert = (raw >= thr).astype(int)
        y = part[C.TARGET].to_numpy()

        m = evaluate(y, alert, raw)
        m["roc_auc_calibrated"] = float(np.nan if len(set(y)) < 2 else
                                        __import__("sklearn.metrics", fromlist=["x"])
                                        .roc_auc_score(y, cal))
        m["pr_auc_lift_over_base_rate"] = round(m["pr_auc"] / m["base_rate"], 2) \
            if m["base_rate"] else float("nan")
        report["splits"][name] = m

        print(f"--- {name.upper()} ---")
        print(f"  ROC-AUC {m['roc_auc']:.4f}   PR-AUC {m['pr_auc']:.6f}  "
              f"(base rate {m['base_rate']:.6f}, lift {m['pr_auc_lift_over_base_rate']}x)")
        print(f"  recall  {m['recall']:.4f}   precision {m['precision']:.6f}   "
              f"F1 {m['f1']:.6f}   Brier {m['brier']:.6f}")
        print(f"  TP={m['tp']}  FP={m['fp']:,}  FN={m['fn']}  TN={m['tn']:,}")

        if name == "test":
            report["operational"]["event_detection"] = event_level_detection(part, alert)
            report["operational"]["alert_burden"] = alert_burden(part, alert)
            report["errors"] = error_analysis(part, raw, alert)

    # Reference baselines on the SAME locked test split, fitted only on train.
    print("\n--- REFERENCE BASELINES on the locked test split ---")
    for bname, s in baseline_scores(train, test).items():
        yb = test[C.TARGET].to_numpy()
        mb = evaluate(yb, (s >= np.nanmedian(s)).astype(int), np.nan_to_num(s))
        report["baselines"][bname] = mb
        print(f"  {bname:30s} ROC-AUC {mb['roc_auc']:.4f}  PR-AUC {mb['pr_auc']:.6f}")

    ml_pr = report["splits"]["test"]["pr_auc"]
    best_b = max(report["baselines"].items(), key=lambda kv: kv[1]["pr_auc"])
    report["verdict"] = {
        "model_test_pr_auc": ml_pr,
        "best_baseline": best_b[0],
        "best_baseline_test_pr_auc": best_b[1]["pr_auc"],
        "model_beats_best_baseline_on_test": bool(ml_pr > best_b[1]["pr_auc"]),
        "pr_auc_ratio_model_over_baseline": round(ml_pr / best_b[1]["pr_auc"], 3)
        if best_b[1]["pr_auc"] else float("nan"),
        "note": (
            "Test figures are reported once and were not used for any selection. "
            "The baseline comparison is the scientifically load-bearing result: a model "
            "that does not beat a day-of-year climatology has not demonstrated "
            "flood-prediction skill, whatever its ROC-AUC."
        ),
    }

    ev = report["operational"]["event_detection"]
    ab = report["operational"]["alert_burden"]
    print("\n--- OPERATIONAL READ (test split) ---")
    print(f"  events in split          : {ev['events']}")
    print(f"  events detected          : {ev['detected']}  "
          f"({ev['event_detection_rate']:.1%})" if ev["events"] else "  n/a")
    print(f"  median / mean lead days  : {ev['median_lead_days']} / {ev['mean_lead_days']}")
    print(f"  alerts per location/year : {ab['alerts_per_location_per_year']}")
    print(f"  i.e. one alert every     : {ab['days_between_alerts_per_location']} days per location")

    print(f"\n  MODEL   test PR-AUC {ml_pr:.6f}")
    print(f"  BEST BASELINE ({best_b[0]}) test PR-AUC {best_b[1]['pr_auc']:.6f}")
    print(f"  model beats baseline: {report['verdict']['model_beats_best_baseline_on_test']}")

    out = C.REPORTS_DIR / "final_evaluation.json"
    out.write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
