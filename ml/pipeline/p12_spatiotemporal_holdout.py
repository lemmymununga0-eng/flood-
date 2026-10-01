"""Spatio-temporal holdout - unseen province AND unseen future, simultaneously.

Why this exists: p11_spatial_holdout.py holds out PLACE but not TIME. It trains on nine
provinces across all years and evaluates the tenth across those same years, so when it
scores January 2013 in Lusaka the model has already seen January 2013 floods in Central.
Zambian weather is nationally correlated, so that is contemporaneous information which
would not exist operationally. The spatial result is therefore evidence of spatial
transfer GIVEN same-period data, not evidence of forecasting skill, and it must not be
read as the latter.

This script removes that confound. For each province P:

    train on   : every OTHER province, restricted to the TRAINING period only
    evaluate on: province P, restricted to the VALIDATION period only

so the evaluation rows are unseen in both dimensions at once. That is the real
deployment condition: a district the model has no flood history for, in a period after
everything it was fitted on.

The test split is not read.

    python ml/pipeline/p12_spatiotemporal_holdout.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.preprocessing import RobustScaler  # noqa: E402

from ml import config as C  # noqa: E402
from ml.pipeline.p10_experiments import (  # noqa: E402
    FEATURE_SETS, attach_climatology, baseline_scores, evaluate, load, usable,
)
from ml.pipeline.p11_spatial_holdout import province_map  # noqa: E402
from ml.pipeline.p15_finalize import fit_model  # noqa: E402

FEATURE_SETS_TO_TEST = ["F_climatology_only", "G_climatology_plus_weather",
                        "H_climatology_plus_weather_rain_soil"]
MODELS = ["LogisticRegression", "DecisionTree", "XGBoost"]
MIN_POSITIVES = 5


def main() -> None:
    C.ensure_out_dirs()
    train_df = usable(load("train"))
    val_df = usable(load("validation"))
    p = province_map()
    train_df["province"] = train_df.location.map(p).fillna("Unknown")
    val_df["province"] = val_df.location.map(p).fillna("Unknown")

    print("SPATIO-TEMPORAL HOLDOUT - unseen province AND unseen future")
    print(f"  fit window  : {train_df.date.min().date()} -> {train_df.date.max().date()}")
    print(f"  eval window : {val_df.date.min().date()} -> {val_df.date.max().date()}")
    print(f"  provinces   : {val_df.province.nunique()}")
    print("  TEST SPLIT UNTOUCHED.\n")

    rows = []
    for prov in sorted(val_df.province.unique()):
        fit = train_df[train_df.province != prov].copy()     # other provinces, past only
        ev = val_df[val_df.province == prov].copy()          # this province, future only
        pos = int(ev[C.TARGET].sum())
        if pos < MIN_POSITIVES or fit.empty:
            rows.append({"province": prov, "status": "skipped", "positives": pos,
                         "reason": f"{pos} positives < {MIN_POSITIVES}"})
            print(f"  {prov:16s} SKIPPED ({pos} positives)")
            continue

        # Climatology fitted on the retained provinces' PAST only.
        attach_climatology(fit, ev)

        for bname, s in baseline_scores(fit, ev).items():
            if bname != "seasonal_climatology":
                continue
            m = evaluate(ev[C.TARGET].to_numpy(),
                         (s >= np.nanmedian(s)).astype(int), np.nan_to_num(s))
            rows.append({"province": prov, "status": "ok", "kind": "baseline",
                         "name": bname, "features": "-", **m})

        for fs in FEATURE_SETS_TO_TEST:
            feats = FEATURE_SETS[fs]
            Xtr, ytr = fit[feats].to_numpy(float), fit[C.TARGET].to_numpy()
            scaler = RobustScaler().fit(Xtr)
            Xev, yev = scaler.transform(ev[feats].to_numpy(float)), ev[C.TARGET].to_numpy()
            for mname in MODELS:
                model = fit_model(mname, scaler.transform(Xtr), ytr)
                proba = model.predict_proba(Xev)[:, 1]
                m = evaluate(yev, (proba >= 0.5).astype(int), proba)
                rows.append({"province": prov, "status": "ok", "kind": "model",
                             "name": mname, "features": fs, **m})
        best = max((r for r in rows if r.get("province") == prov
                    and r.get("kind") == "model"),
                   key=lambda r: r.get("pr_auc", 0), default=None)
        bl = next((r for r in rows if r.get("province") == prov
                   and r.get("kind") == "baseline"), None)
        if best and bl:
            print(f"  {prov:16s} pos={pos:>4}  baseline PR-AUC={bl['pr_auc']:.6f}  "
                  f"best model={best['pr_auc']:.6f} ({best['name']}/{best['features']})",
                  flush=True)

    res = pd.DataFrame(rows)
    out = C.REPORTS_DIR / "spatiotemporal_holdout.csv"
    res.to_csv(out, index=False)

    ok = res[res.status == "ok"].dropna(subset=["pr_auc"])
    summary = {}
    if len(ok):
        base = ok[ok.kind == "baseline"].set_index("province").pr_auc
        print("\n--- head-to-head vs each province's own baseline ---")
        for (nm, fs), g in ok[ok.kind == "model"].groupby(["name", "features"]):
            s = g.set_index("province").pr_auc
            common = s.index.intersection(base.index)
            if not len(common):
                continue
            ratio = s[common] / base[common]
            key = f"{nm} / {fs}"
            summary[key] = {
                "provinces": int(len(common)),
                "provinces_beating_baseline": int((s[common] > base[common]).sum()),
                "win_rate": round(float((s[common] > base[common]).mean()), 3),
                "mean_ratio": round(float(ratio.mean()), 3),
                "median_ratio": round(float(ratio.median()), 3),
            }
        for k, v in sorted(summary.items(), key=lambda kv: -kv[1]["win_rate"]):
            print(f"  {k:52s} {v['provinces_beating_baseline']:>2}/{v['provinces']:>2} "
                  f"win={v['win_rate']:.2f} mean_ratio={v['mean_ratio']} "
                  f"median_ratio={v['median_ratio']}")
        (C.REPORTS_DIR / "spatiotemporal_holdout_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
