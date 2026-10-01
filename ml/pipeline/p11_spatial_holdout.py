"""Phase 11 - spatial generalisation as a robustness experiment.

This ADDS to the temporal evaluation, it does not replace it, and it never touches the
locked test split: folds are cut from train + validation only.

The question it answers is the one that actually matters for Zambian deployment: if the
system were pointed at a district whose flood history the model never saw, would it still
rank risk usefully? Leave-one-province-out is the right granularity, because whole
provinces share climate and river systems, so holding out a single district would leave
near-identical neighbours in the training set and overstate generalisation.

    python ml/pipeline/p11_spatial_holdout.py
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
from ml.pipeline.p15_finalize import fit_model  # noqa: E402

FEATURE_SET = "H_climatology_plus_weather_rain_soil"
MODELS = ["LogisticRegression", "XGBoost"]
MIN_POSITIVES = 5


def province_map() -> dict[str, str]:
    d = pd.read_csv(C.DESINVENTAR_CSV)
    m: dict[str, str] = {}
    for row in d.itertuples():
        dist = str(getattr(row, "district", "") or "").strip()
        prov = str(getattr(row, "province", "") or "").strip()
        if dist and prov and dist not in m:
            m[dist] = prov
    return m


def main() -> None:
    C.ensure_out_dirs()
    df = pd.concat([usable(load("train")), usable(load("validation"))], ignore_index=True)
    df["province"] = df.location.map(province_map()).fillna("Unknown")
    feats = FEATURE_SETS[FEATURE_SET]

    print(f"spatial holdout on {FEATURE_SET} ({len(feats)} features), "
          f"train+validation only. TEST SPLIT UNTOUCHED.")
    print(f"rows={len(df):,} provinces={df.province.nunique()} "
          f"locations={df.location.nunique()}\n")

    rows = []
    for prov, held in df.groupby("province", sort=True):
        keep = df[df.province != prov]
        pos = int(held[C.TARGET].sum())
        if pos < MIN_POSITIVES or len(keep) == 0:
            rows.append({"province": prov, "status": "skipped", "positives": pos,
                         "reason": f"{pos} positives < {MIN_POSITIVES}",
                         "locations": int(held.location.nunique())})
            print(f"  {prov:22s} SKIPPED ({pos} positives)")
            continue

        keep, held = keep.copy(), held.copy()
        # Climatology learned only from the retained provinces, so the held-out province
        # contributes nothing to the baseline information the model is handed.
        attach_climatology(keep, held)

        Xtr = keep[feats].to_numpy(float)
        ytr = keep[C.TARGET].to_numpy()
        scaler = RobustScaler().fit(Xtr)
        Xh, yh = scaler.transform(held[feats].to_numpy(float)), held[C.TARGET].to_numpy()

        # Reference: the same seasonal baseline, also fitted without this province.
        for bname, s in baseline_scores(keep, held).items():
            if bname != "seasonal_climatology":
                continue
            mb = evaluate(yh, (s >= np.nanmedian(s)).astype(int), np.nan_to_num(s))
            rows.append({"province": prov, "status": "ok", "kind": "baseline",
                         "name": bname, "locations": int(held.location.nunique()), **mb})

        for mname in MODELS:
            model = fit_model(mname, scaler.transform(Xtr), ytr)
            proba = model.predict_proba(Xh)[:, 1]
            m = evaluate(yh, (proba >= 0.5).astype(int), proba)
            rows.append({"province": prov, "status": "ok", "kind": "model",
                         "name": mname, "locations": int(held.location.nunique()), **m})
            print(f"  {prov:22s} {mname:20s} ROC-AUC={m['roc_auc']:.4f} "
                  f"PR-AUC={m['pr_auc']:.6f} pos={m['positives']}", flush=True)

    res = pd.DataFrame(rows)
    out = C.REPORTS_DIR / "spatial_holdout.csv"
    res.to_csv(out, index=False)

    ok = res[res.status == "ok"]
    summary = {}
    if len(ok):
        g = (ok.groupby(["kind", "name"])[["roc_auc", "pr_auc"]]
             .agg(["count", "mean", "std", "min", "max"]).round(5))
        print("\n--- leave-one-province-out distribution ---")
        print(g.to_string())
        summary = json.loads(g.to_json())
        (C.REPORTS_DIR / "spatial_holdout_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
