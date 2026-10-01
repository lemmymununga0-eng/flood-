"""Formal deployment go/no-go, decided against pre-declared evidence criteria.

"Only deploy a model if the evidence supports it" needs the standard of evidence fixed in
advance, otherwise the standard drifts to whatever the results happen to clear. The five
criteria below are written here, in code, and are applied mechanically. None of them is a
judgement call made after seeing a number.

  C1  INCREMENTAL SKILL    Given the seasonal climatology as an input feature, a model
                           using weather must beat climatology-alone on validation PR-AUC
                           by at least MIN_INCREMENTAL_GAIN. This is the core question:
                           does weather add anything the calendar does not already have?

  C2  TEMPORAL STABILITY   Across rolling-origin folds, that model must beat the best
                           baseline in at least MIN_WIN_RATE of folds. A single lucky
                           window is not skill.

  C3  SPATIAL GENERALISATION  Mean leave-one-province-out PR-AUC must exceed the
                           corresponding baseline. A model that only works where it has
                           seen floods before cannot be pointed at a new district.

  C4  USABLE RECALL        Validation recall >= MIN_RECALL. A model that ranks well but
                           finds almost nothing is not operationally meaningful.

  C5  ALERT BURDEN         There must exist a threshold achieving C4's recall within
                           MAX_ALERTS_PER_LOCATION_PER_YEAR. An unusable alert rate is a
                           disqualification, not a tuning detail.

ALL FIVE must pass. The test split is not read by this script under any circumstance.

    python ml/pipeline/p16_deployment_decision.py
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402
from ml.pipeline.p10_experiments import INCREMENTAL_SETS  # noqa: E402

MIN_INCREMENTAL_GAIN = 0.05      # 5% relative PR-AUC over climatology-alone
MIN_WIN_RATE = 0.60              # beat the baseline in 60% of rolling folds
MIN_RECALL = 0.30
MAX_ALERTS_PER_LOCATION_PER_YEAR = 6.0

CONTROL = "F_climatology_only"


def _load_csv(name: str) -> pd.DataFrame | None:
    p = C.REPORTS_DIR / name
    return pd.read_csv(p) if p.exists() else None


def _load_json(name: str) -> dict | None:
    p = C.REPORTS_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def criterion_1(abl: pd.DataFrame, roll: dict | None) -> dict:
    """Incremental skill over climatology-as-a-feature.

    Revised 2026-10-01. The first version of this check read the FIXED-SPLIT ablation
    only, and it passed: DecisionTree / G_climatology_plus_weather scored +94.8% over the
    control. Rolling-origin validation then showed that same configuration winning just
    1 fold in 15, with a mean PR-AUC ratio of 0.649 -- i.e. the +94.8% was noise from one
    window of 331 positives. A criterion that can be cleared by a result the very next
    criterion refutes is not a criterion, so C1 now requires BOTH:

        (a) a fixed-split gain over the control, AND
        (b) corroboration across rolling folds -- the same configuration must have a
            mean PR-AUC ratio of at least 1.0 against the per-fold baseline.

    (b) is what single-window evidence cannot fake.
    """
    inc = abl[abl.features.isin(INCREMENTAL_SETS)].dropna(subset=["pr_auc"])
    if inc.empty:
        return {"pass": False, "reason": "incremental-skill feature sets were not run"}
    ctrl = inc[inc.features == CONTROL]
    if ctrl.empty:
        return {"pass": False, "reason": f"control {CONTROL} missing"}
    ctrl_pr = float(ctrl.pr_auc.max())
    cand = inc[inc.features != CONTROL]
    if cand.empty:
        return {"pass": False, "reason": "no weather-augmented candidate was run"}

    best = cand.loc[cand.pr_auc.idxmax()]
    gain = float(best.pr_auc) / ctrl_pr - 1.0
    key = f"{best['name']} / {best.features}"
    fixed_split_ok = gain >= MIN_INCREMENTAL_GAIN

    corroborated, ratio = False, None
    if roll and "head_to_head" in roll and key in roll["head_to_head"]:
        ratio = roll["head_to_head"][key].get("mean_pr_auc_ratio")
        corroborated = bool(ratio is not None and ratio >= 1.0)

    return {
        "pass": bool(fixed_split_ok and corroborated),
        "control_pr_auc": round(ctrl_pr, 6),
        "best_candidate": key,
        "candidate_pr_auc": round(float(best.pr_auc), 6),
        "fixed_split_relative_gain": round(gain, 4),
        "required_gain": MIN_INCREMENTAL_GAIN,
        "fixed_split_gain_met": fixed_split_ok,
        "rolling_mean_pr_auc_ratio": ratio,
        "rolling_corroborated": corroborated,
        "candidate_recall": round(float(best.recall), 4),
        "note": ("A fixed-split gain alone is insufficient: this candidate's +94.8% on one "
                 "window corresponded to 1 win in 15 rolling folds."
                 if fixed_split_ok and not corroborated else ""),
    }


def criterion_2(roll: dict | None, candidate: str | None) -> dict:
    if not roll or "head_to_head" not in roll:
        return {"pass": False, "reason": "rolling-origin validation has not been run"}
    h2h = roll["head_to_head"]
    if not h2h:
        return {"pass": False, "reason": "no rolling-origin head-to-head rows"}
    best_key = max(h2h, key=lambda k: h2h[k]["win_rate"])
    best = h2h[best_key]
    return {
        "pass": bool(best["win_rate"] >= MIN_WIN_RATE),
        "best_by_win_rate": best_key,
        "folds": best["folds"],
        "folds_beating_baseline": best["folds_beating_baseline"],
        "win_rate": best["win_rate"],
        "required_win_rate": MIN_WIN_RATE,
        "mean_pr_auc_ratio": best.get("mean_pr_auc_ratio"),
        "all_candidates": h2h,
    }


def criterion_3(st: dict | None, spatial: pd.DataFrame | None) -> dict:
    """Spatial generalisation, judged on the SPATIO-TEMPORAL holdout.

    Revised 2026-10-01. This previously read p11_spatial_holdout.py, which holds out place
    but not time: it trains on nine provinces across all years and evaluates the tenth
    across those same years, so the model sees contemporaneous floods from correlated
    neighbouring provinces. That is not available operationally, so a pass there did not
    license deployment. C3 now reads p12_spatiotemporal_holdout.py, where the evaluation
    rows are unseen in BOTH dimensions.

    Judged on median ratio, not mean: the place-only run had a single province (Copperbelt)
    at 10.3x that dragged XGBoost's mean from 1.37 to 2.26.
    """
    if not st:
        return {"pass": False,
                "reason": "spatio-temporal holdout has not been run; the place-only "
                          "spatial result does not substitute for it"}
    best_key = max(st, key=lambda k: st[k]["median_ratio"])
    best = st[best_key]
    out = {
        "pass": bool(best["median_ratio"] > 1.0),
        "basis": "spatio-temporal holdout (unseen province AND unseen future)",
        "best_candidate": best_key,
        "provinces": best["provinces"],
        "provinces_beating_baseline": best["provinces_beating_baseline"],
        "win_rate": best["win_rate"],
        "median_ratio": best["median_ratio"],
        "mean_ratio": best["mean_ratio"],
    }
    if spatial is not None:
        ok = spatial[spatial.status == "ok"].dropna(subset=["pr_auc"])
        if not ok.empty:
            out["place_only_reference"] = (
                "The place-only holdout was more favourable (LR beat the baseline in 9/10 "
                "provinces, median ratio 1.11), but it leaks contemporaneous signal and is "
                "recorded for contrast only, not counted toward this criterion.")
    return out


def criterion_4(c1: dict) -> dict:
    r = c1.get("candidate_recall")
    return {"pass": bool(r is not None and r >= MIN_RECALL),
            "candidate_recall": r, "required_recall": MIN_RECALL}


def criterion_5() -> dict:
    sweep = _load_csv("threshold_sweep_validation.csv")
    if sweep is None:
        return {"pass": False,
                "reason": "no validation threshold sweep exists (p15_finalize.py has not "
                          "produced one, which itself means no model was selected)"}
    ok = sweep[(sweep.alerts_per_location_per_year <= MAX_ALERTS_PER_LOCATION_PER_YEAR)
               & (sweep.recall >= MIN_RECALL)]
    return {
        "pass": bool(len(ok) > 0),
        "budget": MAX_ALERTS_PER_LOCATION_PER_YEAR,
        "thresholds_meeting_budget_and_recall": int(len(ok)),
        "best_recall_within_budget": round(float(ok.recall.max()), 4) if len(ok) else 0.0,
    }


def main() -> None:
    C.ensure_out_dirs()
    abl = _load_csv("validation_ablation.csv")
    if abl is None:
        raise SystemExit("run ml/pipeline/p10_experiments.py first")
    roll = _load_json("rolling_origin_summary.json")
    spatial = _load_csv("spatial_holdout.csv")
    st = _load_json("spatiotemporal_holdout_summary.json")

    c1 = criterion_1(abl, roll)
    c2 = criterion_2(roll, c1.get("best_candidate"))
    c3 = criterion_3(st, spatial)
    c4 = criterion_4(c1)
    c5 = criterion_5()

    checks = {
        "C1_incremental_skill": c1, "C2_temporal_stability": c2,
        "C3_spatial_generalisation": c3, "C4_usable_recall": c4,
        "C5_alert_burden": c5,
    }
    passed = [k for k, v in checks.items() if v.get("pass")]
    deploy = len(passed) == len(checks)

    verdict = {
        "decided": str(date.today()),
        "decision": "DEPLOY" if deploy else "DO_NOT_DEPLOY",
        "criteria_passed": f"{len(passed)}/{len(checks)}",
        "passed": passed,
        "failed": [k for k in checks if k not in passed],
        "thresholds_declared_in_advance": {
            "MIN_INCREMENTAL_GAIN": MIN_INCREMENTAL_GAIN,
            "MIN_WIN_RATE": MIN_WIN_RATE, "MIN_RECALL": MIN_RECALL,
            "MAX_ALERTS_PER_LOCATION_PER_YEAR": MAX_ALERTS_PER_LOCATION_PER_YEAR,
        },
        "checks": checks,
        "test_split_used": False,
    }
    out = C.REPORTS_DIR / "deployment_decision.json"
    out.write_text(json.dumps(verdict, indent=2, default=float), encoding="utf-8")

    bar = "=" * 74
    print(bar)
    print(f"DEPLOYMENT DECISION: {verdict['decision']}   "
          f"({verdict['criteria_passed']} criteria passed)")
    print(bar)
    for name, chk in checks.items():
        mark = "PASS" if chk.get("pass") else "FAIL"
        print(f"\n[{mark}] {name}")
        for k, v in chk.items():
            if k in ("pass", "all_candidates"):
                continue
            print(f"        {k:38s} {v}")
    print(f"\nWrote {out}")

    if not deploy:
        print("\nNo model is promoted. The honest reading is that the evidence does not "
              "support deployment, and the negative result stands as the finding.")


if __name__ == "__main__":
    main()
