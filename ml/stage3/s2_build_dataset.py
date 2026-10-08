"""Stage 3, step 2 — the forecasting dataset.

One row per (district, prediction_date). Every predictor describes information that
would genuinely have been available on that date; every target looks forward.

LEAKAGE CONTROLS, and why each exists
-------------------------------------
* Rolling/lag features use `.rolling(w)` and `.shift(k)` grouped per district, with no
  centring and no negative shift, so a window ending at t contains only days <= t.
  `test_s3_leakage.py` asserts this against a deliberately forward-shifted control.
* Rainfall ANOMALY is computed against a TRAILING 365-day mean, not a whole-period
  climatology. A whole-period mean would embed information from after t, and would also
  differ per rolling-origin fold. A trailing mean is causal by construction.
* ONI is lagged to month(t)-2: the collection's leakage register records that an ONI
  season centred on month m is not final until m+1.
* Nino 3.4 / DMI are lagged to month(t)-1 for the same reason.
* `location_master.n_flood_records` and `n_flood_records_day_precision` are EXCLUDED.
  They count every flood in the archive, including ones after t — a direct target leak.
* DesInventar consequence fields (deaths, damage, affected) never enter: they are
  post-event by definition. They are not read by this script at all.
* JRC surface-water occurrence aggregates 1984-2021, which spans the event period. It is
  kept only as STATIC susceptibility and is confined to its own feature set so its
  contribution can be isolated rather than assumed harmless.

TARGETS
-------
For each horizon h: target_h = 1 if a POSITIVE district-day falls in (t, t+h].
`usable_h` = 0 when that window overlaps a MASK interval and contains no positive — those
rows are excluded from training and from every evaluation, never scored as negatives.

    python ml/stage3/s2_build_dataset.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402

RAIN_WINDOWS = (1, 3, 7, 14, 30)
SOIL_COLS = ["GWETTOP", "GWETROOT", "GWETPROF"]
WEATHER_COLS = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"]

# Never features. Kept here as an explicit deny-list so the exclusion is visible.
FORBIDDEN = {"n_flood_records", "n_flood_records_day_precision"}


def load_daily() -> pd.DataFrame:
    print("loading daily inputs ...")
    ch = pd.read_csv(C.S3_CHIRPS, usecols=["location_id", "date", "chirps_precip_mm"],
                     parse_dates=["date"])
    pw = pd.read_csv(C.S3_POWER, usecols=["location_id", "date"] + WEATHER_COLS,
                     parse_dates=["date"])
    so = pd.read_csv(C.S3_SOIL, usecols=["location_id", "date"] + SOIL_COLS,
                     parse_dates=["date"])
    print(f"  chirps {len(ch):,}  power {len(pw):,}  soil {len(so):,}")

    df = ch.merge(pw, on=["location_id", "date"], how="outer") \
           .merge(so, on=["location_id", "date"], how="outer")
    df = df.sort_values(["location_id", "date"]).reset_index(drop=True)
    print(f"  merged {len(df):,} rows, {df.location_id.nunique()} districts, "
          f"{df.date.min().date()} -> {df.date.max().date()}")
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    print("engineering leakage-safe features ...")
    g = df.groupby("location_id", sort=False)

    # --- rainfall history (CHIRPS is the gauge-corrected product; keep POWER too) ---
    for w in RAIN_WINDOWS:
        df[f"chirps_sum_{w}d"] = g["chirps_precip_mm"].transform(
            lambda s, w=w: s.rolling(w, min_periods=w).sum())
        df[f"power_sum_{w}d"] = g["PRECTOTCORR"].transform(
            lambda s, w=w: s.rolling(w, min_periods=w).sum())
    df["chirps_max_7d"] = g["chirps_precip_mm"].transform(
        lambda s: s.rolling(7, min_periods=7).max())
    df["chirps_max_30d"] = g["chirps_precip_mm"].transform(
        lambda s: s.rolling(30, min_periods=30).max())
    df["wet_days_30d"] = g["chirps_precip_mm"].transform(
        lambda s: (s > 1.0).rolling(30, min_periods=30).sum())

    # --- anomaly against a TRAILING climatology (causal; see module docstring) ---
    trail = g["chirps_precip_mm"].transform(
        lambda s: s.rolling(365, min_periods=180).mean())
    df["chirps_anom_7d"] = df["chirps_sum_7d"] - 7 * trail
    df["chirps_anom_30d"] = df["chirps_sum_30d"] - 30 * trail
    df["chirps_trailing_365d_mean"] = trail

    # --- antecedent wetness, lagged one day so day t's own reading is not assumed ---
    for c in SOIL_COLS:
        df[f"{c.lower()}_lag1"] = g[c].shift(1)
        df[f"{c.lower()}_mean_7d"] = g[c].transform(
            lambda s: s.shift(1).rolling(7, min_periods=7).mean())

    # --- seasonality (a calendar fact, available at t) ---
    doy = df.date.dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["is_wet_season"] = df.date.dt.month.isin([11, 12, 1, 2, 3, 4]).astype(int)
    return df


def add_static(df: pd.DataFrame) -> pd.DataFrame:
    print("joining static district attributes ...")
    terr = pd.read_csv(C.S3_TERRAIN)
    land = pd.read_csv(C.S3_LANDCOVER)
    surf = pd.read_csv(C.S3_SURFACE_WATER)
    for name, t in (("terrain", terr), ("landcover", land), ("surface_water", surf)):
        drop = [c for c in t.columns if c in FORBIDDEN]
        if drop:
            print(f"  EXCLUDED from {name}: {drop}")
            t = t.drop(columns=drop)
        num = [c for c in t.columns
               if c != "location_id" and pd.api.types.is_numeric_dtype(t[c])]
        df = df.merge(t[["location_id"] + num], on="location_id", how="left")
    return df


def add_climate(df: pd.DataFrame) -> pd.DataFrame:
    print("joining climate indices (lagged) ...")
    cl = pd.read_csv(C.S3_CLIMATE)
    cl["ym"] = pd.to_datetime(
        dict(year=cl.year, month=cl.month, day=1)).dt.to_period("M")
    df["ym"] = df.date.dt.to_period("M")

    # ONI needs month m+1 to finalise -> only safe at month(t)-2.
    oni = cl[["ym", "oni"]].copy()
    oni["ym"] = oni["ym"] + 2
    df = df.merge(oni.rename(columns={"oni": "oni_lag2m"}), on="ym", how="left")

    # Nino 3.4 / DMI are monthly means -> safe at month(t)-1.
    for col, out in (("nino34_anom", "nino34_lag1m"), ("dmi_hadisst", "dmi_lag1m")):
        if col in cl.columns:
            t = cl[["ym", col]].copy()
            t["ym"] = t["ym"] + 1
            df = df.merge(t.rename(columns={col: out}), on="ym", how="left")
    return df.drop(columns=["ym"])


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    print("building three-state targets ...")
    pos = pd.read_csv(C.S3_OUT_PROCESSED / "labels_positive_district_days.csv",
                      parse_dates=["date"])
    msk = pd.read_csv(C.S3_OUT_PROCESSED / "labels_mask_intervals.csv",
                      parse_dates=["start", "end"])

    df["is_flood_day"] = 0
    key = pd.MultiIndex.from_frame(df[["location_id", "date"]])
    pkey = pd.MultiIndex.from_frame(pos[["location_id", "date"]])
    df.loc[key.isin(pkey), "is_flood_day"] = 1
    print(f"  flood days matched into the grid: {int(df.is_flood_day.sum())} "
          f"(of {len(pos)} labelled)")

    df["is_masked_day"] = 0
    loc_arr, date_arr = df.location_id.values, df.date.values
    for r in msk.itertuples():
        sel = ((loc_arr == r.location_id) & (date_arr >= np.datetime64(r.start))
               & (date_arr <= np.datetime64(r.end)))
        if sel.any():
            df.loc[sel, "is_masked_day"] = 1
    # A documented onset always outranks a coarser overlapping mask.
    df.loc[df.is_flood_day == 1, "is_masked_day"] = 0
    print(f"  masked days: {int(df.is_masked_day.sum()):,} "
          f"({df.is_masked_day.mean():.2%} of the grid)")

    g = df.groupby("location_id", sort=False)

    def forward_max(s: pd.Series, h: int) -> pd.Series:
        """Max over (t, t+h] — reverse, shift off the current row, roll back, reverse."""
        rev = s.iloc[::-1]
        return rev.shift(1).rolling(h, min_periods=1).max().iloc[::-1]

    for h in C.S3_HORIZONS:
        df[f"target_h{h}"] = g["is_flood_day"].transform(
            lambda s, h=h: forward_max(s, h)).fillna(0).astype(int)
        maskwin = g["is_masked_day"].transform(
            lambda s, h=h: forward_max(s, h)).fillna(0).astype(int)
        df[f"usable_h{h}"] = (~((maskwin == 1) & (df[f"target_h{h}"] == 0))).astype(int)
    return df


def main() -> None:
    C.ensure_s3_dirs()
    df = load_daily()
    df = add_features(df)
    df = add_static(df)
    df = add_climate(df)
    df = add_targets(df)

    required = ([f"chirps_sum_{w}d" for w in RAIN_WINDOWS] + WEATHER_COLS
                + ["chirps_anom_7d", "gwetroot_lag1"])
    before = len(df)
    df = df.dropna(subset=[c for c in required if c in df.columns]).reset_index(drop=True)
    print(f"\ndropped {before - len(df):,} rows missing a required predictor "
          f"(rolling warm-up); {len(df):,} remain")

    out = C.S3_OUT_PROCESSED / "forecasting_dataset.parquet"
    try:
        df.to_parquet(out, index=False)
    except Exception:
        out = C.S3_OUT_PROCESSED / "forecasting_dataset.csv"
        df.to_csv(out, index=False)

    summary = {"rows": int(len(df)), "districts": int(df.location_id.nunique()),
               "date_range": [str(df.date.min().date()), str(df.date.max().date())],
               "features": int(len(df.columns)), "horizons": {}}
    print(f"\n{'horizon':>8} {'usable rows':>12} {'positives':>10} {'rate':>10} {'masked out':>11}")
    for h in C.S3_HORIZONS:
        u = df[df[f"usable_h{h}"] == 1]
        summary["horizons"][f"h{h}"] = {
            "usable_rows": int(len(u)), "positives": int(u[f"target_h{h}"].sum()),
            "positive_rate": round(float(u[f"target_h{h}"].mean()), 8),
            "masked_rows": int((df[f"usable_h{h}"] == 0).sum()),
        }
        s = summary["horizons"][f"h{h}"]
        print(f"{'H+'+str(h):>8} {s['usable_rows']:>12,} {s['positives']:>10,} "
              f"{s['positive_rate']:>9.5%} {s['masked_rows']:>11,}")

    (C.S3_OUT_PROCESSED / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
