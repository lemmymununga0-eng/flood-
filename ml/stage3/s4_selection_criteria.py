"""Stage 3, step 4 — the model-selection gate (§31).

WRITTEN BEFORE THE EXPERIMENT RESULTS WERE SEEN. The thresholds below were committed
while the H+7 sweep was still running, so they cannot have been fitted to whatever the
numbers turned out to be. That is the entire value of this file: a criterion chosen after
seeing results is not a criterion.

A model is eligible for deployment at a horizon only if it clears ALL SIX gates.

  G1  BEATS THE BASELINE       mean PR-AUC across folds must exceed the best per-fold
                               baseline (seasonal climatology, rainfall rule, district
                               event frequency) by >= MIN_PR_AUC_GAIN relative.
                               §24: ML must demonstrate meaningful improvement over an
                               appropriate simple baseline.

  G2  CONSISTENTLY             must beat that baseline in >= MIN_WIN_RATE of folds. A
                               mean carried by one lucky year is not skill; the earlier
                               Stage-2 study produced exactly that trap (+94.8% on one
                               window, 1 win in 15 folds).

  G3  FINDS FLOODS             mean recall >= MIN_RECALL. A model that ranks acceptably
                               but detects almost nothing is not operationally meaningful.

  G4  REJECTS NON-FLOODS       mean specificity >= MIN_SPECIFICITY. §26: the objective is
                               not to issue many warnings. Both classes must be tested.

  G5  USABLE ALERT BURDEN      implied false alarms <= MAX_FP_PER_DISTRICT_YEAR. A
                               precision figure alone hides what an operator would live
                               with; this expresses it in alerts.

  G6  ENOUGH EVIDENCE          >= MIN_FOLDS evaluable folds, and >= MIN_TOTAL_POSITIVES
                               positives across them, or the result is noise regardless
                               of its value.

If no model clears all six at a horizon, the correct output is NO_MODEL_SELECTED for that
horizon. That is a result, not a failure.

    python ml/stage3/s4_selection_criteria.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402

# --- pre-declared thresholds ------------------------------------------------
MIN_PR_AUC_GAIN = 0.10          # 10% relative over the best baseline
MIN_WIN_RATE = 0.60             # beats it in 60% of folds
MIN_RECALL = 0.30
MIN_SPECIFICITY = 0.70
MAX_FP_PER_DISTRICT_YEAR = 12   # roughly one false alarm a month per district
MIN_FOLDS = 8
MIN_TOTAL_POSITIVES = 50

CRITERIA = {
    "MIN_PR_AUC_GAIN": MIN_PR_AUC_GAIN, "MIN_WIN_RATE": MIN_WIN_RATE,
    "MIN_RECALL": MIN_RECALL, "MIN_SPECIFICITY": MIN_SPECIFICITY,
    "MAX_FP_PER_DISTRICT_YEAR": MAX_FP_PER_DISTRICT_YEAR,
    "MIN_FOLDS": MIN_FOLDS, "MIN_TOTAL_POSITIVES": MIN_TOTAL_POSITIVES,
    "declared_before_results": True,
}


def assess(res: pd.DataFrame, horizon: int, n_districts: int = 101) -> dict:
    hh = res[(res.horizon == horizon) & (res.status == "ok")].dropna(subset=["pr_auc"])
    if hh.empty:
        return {"horizon": horizon, "decision": "NO_MODEL_SELECTED",
                "reason": "no evaluable folds"}

    base = hh[hh.kind == "baseline"].groupby("fold_year").pr_auc.max()
    base_name = (hh[hh.kind == "baseline"].groupby("name").pr_auc.mean()
                 .sort_values(ascending=False))

    candidates = []
    for (nm, fs), g in hh[hh.kind == "model"].groupby(["name", "features"]):
        g = g.set_index("fold_year")
        common = g.index.intersection(base.index)
        if not len(common):
            continue
        pr, bl = g.pr_auc[common], base[common]
        gain = float(pr.mean() / bl.mean() - 1) if bl.mean() else float("nan")
        win = float((pr > bl).mean())
        rec, spec = float(g.recall[common].mean()), float(g.specificity[common].mean())
        fp_year = float(g.fp[common].sum() / max(len(common), 1) / n_districts)
        pos = int(g.positives[common].sum())

        checks = {
            "G1_beats_baseline": bool(gain >= MIN_PR_AUC_GAIN),
            "G2_consistently": bool(win >= MIN_WIN_RATE),
            "G3_finds_floods": bool(rec >= MIN_RECALL),
            "G4_rejects_non_floods": bool(spec >= MIN_SPECIFICITY),
            "G5_usable_alert_burden": bool(fp_year <= MAX_FP_PER_DISTRICT_YEAR),
            "G6_enough_evidence": bool(len(common) >= MIN_FOLDS
                                       and pos >= MIN_TOTAL_POSITIVES),
        }
        candidates.append({
            "model": nm, "features": fs, "folds": int(len(common)),
            "mean_pr_auc": round(float(pr.mean()), 6),
            "baseline_mean_pr_auc": round(float(bl.mean()), 6),
            "relative_gain": round(gain, 4), "win_rate": round(win, 3),
            "mean_recall": round(rec, 4), "mean_specificity": round(spec, 4),
            "fp_per_district_year": round(fp_year, 1),
            "total_positives": pos,
            "checks": checks, "gates_passed": sum(checks.values()),
            "eligible": all(checks.values()),
        })

    candidates.sort(key=lambda c: (c["gates_passed"], c["relative_gain"]), reverse=True)
    eligible = [c for c in candidates if c["eligible"]]
    return {
        "horizon": horizon,
        "decision": "SELECTED" if eligible else "NO_MODEL_SELECTED",
        "selected": eligible[0] if eligible else None,
        "best_baseline": str(base_name.index[0]) if len(base_name) else None,
        "best_baseline_mean_pr_auc": round(float(base_name.iloc[0]), 6) if len(base_name) else None,
        "folds_evaluated": int(base.size),
        "candidates": candidates[:10],
    }


def main() -> None:
    C.ensure_s3_dirs()
    p = C.S3_OUT_REPORTS / "rolling_origin_results.csv"
    if not p.exists():
        raise SystemExit(f"missing {p}; run ml/stage3/s3_experiments.py first")
    res = pd.read_csv(p)

    out = {"criteria": CRITERIA, "horizons": {}}
    bar = "=" * 76
    print(bar); print("MODEL SELECTION GATE — criteria declared before results"); print(bar)
    for k, v in CRITERIA.items():
        print(f"  {k:30s} {v}")

    for h in sorted(res.horizon.dropna().unique()):
        a = assess(res, int(h))
        out["horizons"][f"h{int(h)}"] = a
        print(f"\n{bar}\nH+{int(h)}  ->  {a['decision']}   "
              f"({a.get('folds_evaluated', 0)} folds)")
        if a.get("best_baseline"):
            print(f"  best baseline: {a['best_baseline']} "
                  f"(mean PR-AUC {a['best_baseline_mean_pr_auc']})")
        for c in a.get("candidates", [])[:4]:
            failed = [k for k, v in c["checks"].items() if not v]
            print(f"  {c['model']:20s} {c['features']:20s} "
                  f"gates {c['gates_passed']}/6  PR-AUC {c['mean_pr_auc']:.5f} "
                  f"(gain {c['relative_gain']:+.1%}, wins {c['win_rate']:.2f})")
            if failed:
                print(f"      failed: {', '.join(failed)}")

    sel = [h for h, a in out["horizons"].items() if a["decision"] == "SELECTED"]
    out["summary"] = {"horizons_with_a_selected_model": sel,
                      "overall": "SELECTED" if sel else "NO_MODEL_SELECTED"}
    (C.S3_OUT_REPORTS / "selection_decision.json").write_text(
        json.dumps(out, indent=2, default=float), encoding="utf-8")

    print(f"\n{bar}")
    print(f"OVERALL: {out['summary']['overall']}"
          + (f"  (horizons: {', '.join(sel)})" if sel else ""))
    print(bar)
    if not sel:
        print("No model cleared all six pre-declared gates at any horizon. On this\n"
              "evidence the honest result is that the expanded data do not support\n"
              "deployment, and nothing is promoted.")


if __name__ == "__main__":
    main()
