"""Stage 3, step 5 — physical sanity checks on the data and on any fitted model (§32).

These are sanity checks, not a substitute for statistical evaluation, and they never
force a model to behave a particular way. Where behaviour is implausible the finding is
recorded, not corrected by overriding predictions or relabelling.

Two layers:

  DATA  — do the labels sit where hydrology says they should? If the positives were
          noise, rainfall around them would look like any other day. This is a check on
          the LABELS, run before any model exists, and it is the one that matters most:
          a model cannot be better than the thing it is asked to predict.

  MODEL — monotone response to antecedent rainfall, behaviour in the dry season, and
          geographic plausibility, for whichever model the selection gate chose. Skipped
          with a clear message when nothing was selected.

    python ml/stage3/s5_physical_sanity.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402


def load() -> pd.DataFrame:
    """Only the columns these checks use. The full frame is ~84 float64 columns over
    970k rows (~600 MB per slice), which will not co-exist with a running sweep."""
    h = C.S3_PRIMARY_HORIZON
    cols = ["location_id", "date", "is_wet_season",
            "chirps_sum_7d", "chirps_sum_14d", "chirps_sum_30d",
            "chirps_anom_7d", "gwetroot_lag1",
            f"target_h{h}", f"usable_h{h}"]
    df = pd.read_parquet(C.S3_OUT_PROCESSED / "forecasting_dataset.parquet",
                         columns=cols)
    for c in df.columns:
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    return df


def data_checks(df: pd.DataFrame) -> dict:
    out = {}
    h = C.S3_PRIMARY_HORIZON
    u = df[df[f"usable_h{h}"] == 1]
    pos = u[u[f"target_h{h}"] == 1]
    neg = u[u[f"target_h{h}"] == 0]

    print("=== 1. Do positives sit on wetter-than-usual days? ===")
    rows = []
    for col in ("chirps_sum_7d", "chirps_sum_14d", "chirps_sum_30d",
                "chirps_anom_7d", "gwetroot_lag1"):
        if col not in u.columns:
            continue
        p, n = pos[col].median(), neg[col].median()
        ratio = float(p / n) if n else float("nan")
        rows.append({"feature": col, "median_positive": round(float(p), 3),
                     "median_negative": round(float(n), 3),
                     "ratio": round(ratio, 3)})
        print(f"  {col:22s} positives {p:9.3f}   negatives {n:9.3f}   ratio {ratio:6.2f}")
    out["positives_vs_negatives"] = rows

    print("\n=== 2. Seasonality of the labels ===")
    wet = pos.is_wet_season.mean()
    wet_all = u.is_wet_season.mean()
    print(f"  positives in wet season : {wet:.1%}")
    print(f"  all usable rows         : {wet_all:.1%}")
    print(f"  -> floods are {wet / wet_all:.2f}x more concentrated in the wet season")
    out["wet_season"] = {"positive_share": round(float(wet), 4),
                         "base_share": round(float(wet_all), 4),
                         "concentration": round(float(wet / wet_all), 3)}

    print("\n=== 3. Geographic plausibility ===")
    by_loc = u.groupby("location_id")[f"target_h{h}"].agg(["sum", "mean"])
    top = by_loc.sort_values("sum", ascending=False).head(8)
    print(f"  districts with any positive : {(by_loc['sum'] > 0).sum()} of {len(by_loc)}")
    print("  most-affected districts:")
    loc = pd.read_csv(C.S3_LOCATIONS)[["location_id", "district", "province"]]
    for lid, r in top.iterrows():
        nm = loc[loc.location_id == lid]
        label = (f"{nm.district.iloc[0]}, {nm.province.iloc[0]}" if len(nm) else lid)
        print(f"    {label:32s} {int(r['sum']):>5} positive district-days")
    out["districts_with_positives"] = int((by_loc["sum"] > 0).sum())
    out["districts_total"] = int(len(by_loc))

    print("\n=== 4. Dry-season positives (a warning sign if common) ===")
    dry = pos[pos.is_wet_season == 0]
    print(f"  {len(dry)} of {len(pos)} positive rows fall outside Nov-Apr "
          f"({len(dry) / max(len(pos), 1):.1%})")
    out["dry_season_positive_rows"] = int(len(dry))
    return out


def model_checks() -> dict:
    sel_path = C.S3_OUT_REPORTS / "selection_decision.json"
    if not sel_path.exists():
        print("\n=== MODEL CHECKS: skipped — selection has not been run ===")
        return {"status": "selection not run"}
    sel = json.loads(sel_path.read_text(encoding="utf-8"))
    if sel.get("summary", {}).get("overall") != "SELECTED":
        print("\n=== MODEL CHECKS: skipped ===")
        print("  No model cleared the selection gate at any horizon, so there is no")
        print("  fitted model whose physical behaviour it would be meaningful to probe.")
        print("  This is reported, not worked around.")
        return {"status": "NO_MODEL_SELECTED — nothing to probe"}
    return {"status": "a model was selected; per-model probes belong with its artifact"}


def main() -> None:
    C.ensure_s3_dirs()
    df = load()
    print(f"dataset {len(df):,} rows, {df.location_id.nunique()} districts\n")
    out = {"data": data_checks(df), "model": model_checks()}
    (C.S3_OUT_REPORTS / "physical_sanity.json").write_text(
        json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(f"\nWrote {C.S3_OUT_REPORTS / 'physical_sanity.json'}")


if __name__ == "__main__":
    main()
