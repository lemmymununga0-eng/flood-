"""Phase 6, 13 - rebuild the target and the feature matrix from the reconciled labels.

Target (unchanged in definition from the baseline, deliberately -- it was already sound):

    flood_next_7d(l, t) = 1  iff  a reconciled POSITIVE interval for location l
                                  covers any day t' in (t, t+7]

What IS new is the third label state. The baseline had two: positive, and
"everything else is negative". A day-precision event at a district the source never
named, or a year-precision event, was silently counted as a negative -- which asserts
that no flood happened when the source says one did. This build carries:

    flood_next_7d  0/1   the target
    label_usable   0/1   0 when the (t, t+7] window overlaps a MASK interval and
                         contains no POSITIVE day. Those rows are excluded from
                         training AND from evaluation -- not relabelled, not deleted,
                         just not asserted either way.

Every feature is strictly backward-looking (dated <= t). Rolling sums use
pandas .rolling() with no centring and no negative shift, grouped per location so no
location's history bleeds into another's. Climate indices are lagged by whole months so
a row never sees an index value finalised after its own date; lag-0 columns are built
but marked unsafe and excluded from every feature set.

    python ml/pipeline/p06_build_dataset.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402

RAW_WEATHER = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"]
SOIL = ["GWETROOT", "GWETPROF", "GWETTOP"]
RAIN_WINDOWS = (3, 7, 14, 30)
REQUIRED = RAW_WEATHER + ["rain_3day", "rain_7day", "rain_14day", "rain_30day",
                          "nino34_lag1m", "dmi_lag1m", "nino34_lag3m", "dmi_lag3m"]


def load_weather() -> pd.DataFrame:
    """Prefer the completed 82-location export when p05 has produced it.

    The research bundle's own export covers only 59 of the 82 locations because its fetch
    aborted on a DNS failure. Training on 59 would be an undocumented reduction in spatial
    coverage, so which file was used is printed rather than left implicit.
    """
    completed = C.PROCESSED_DIR / "weather_complete.csv"
    path = completed if completed.exists() else C.WEATHER_CSV
    df = pd.read_csv(path, parse_dates=["date"], low_memory=False)
    df = df.sort_values(["location", "date"]).reset_index(drop=True)
    expected = pd.read_csv(C.LOCATIONS_CSV).name.nunique()
    print(f"  source: {path.name}")
    print(f"  weather rows={len(df):,} locations={df.location.nunique()} of {expected} "
          f"{df.date.min().date()} -> {df.date.max().date()}")
    if df.location.nunique() < expected:
        print(f"  NOTE: {expected - df.location.nunique()} location(s) absent; run "
              f"ml/pipeline/p05_complete_weather_fetch.py to close the gap. "
              f"Results below cover only the locations present.")
    return df


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the reconciled POSITIVE and MASK intervals."""
    auth = pd.read_csv(C.LABELS_DIR / "authoritative_events.csv",
                       parse_dates=["start", "end"])
    df["flood_reliable"] = 0
    df["masked_day"] = 0

    idx = pd.MultiIndex.from_arrays([df.location.values, df.date.values])
    df = df.set_index(idx, drop=False)

    pos = mask = 0
    for r in auth.itertuples():
        sel = (df.location.values == r.location) & \
              (df.date.values >= np.datetime64(r.start)) & \
              (df.date.values <= np.datetime64(r.end))
        if not sel.any():
            continue
        if r.kind == "POSITIVE":
            df.loc[sel, "flood_reliable"] = 1
            pos += int(sel.sum())
        else:
            df.loc[sel, "masked_day"] = 1
            mask += int(sel.sum())

    # A documented positive always wins over a mask: if a source names the day, the day
    # is known, regardless of any coarser overlapping episode.
    df.loc[df.flood_reliable == 1, "masked_day"] = 0
    df = df.reset_index(drop=True)
    print(f"  flood_reliable days = {int(df.flood_reliable.sum()):,}  "
          f"masked days = {int(df.masked_day.sum()):,}")
    return df


def build_target(df: pd.DataFrame) -> pd.DataFrame:
    """flood_next_7d over (t, t+7], plus the usability mask, both computed per location
    by a forward-looking roll on the LABEL only. No feature looks forward."""
    h = C.HORIZON_DAYS

    def fwd_max(s: pd.Series) -> pd.Series:
        # Reverse -> backward rolling over h days excluding the current row -> reverse.
        # shift(-1) before reversing makes the window strictly (t, t+h].
        rev = s.iloc[::-1]
        out = rev.shift(1).rolling(h, min_periods=1).max().iloc[::-1]
        return out

    g = df.groupby("location", sort=False)
    df[C.TARGET] = g["flood_reliable"].transform(fwd_max).fillna(0).astype(int)
    df["_mask_in_window"] = g["masked_day"].transform(fwd_max).fillna(0).astype(int)

    # A row is unusable when its forecast window overlaps something the sources leave
    # undetermined and contains no documented positive.
    df[C.MASK_COL] = (~((df["_mask_in_window"] == 1) & (df[C.TARGET] == 0))).astype(int)
    df = df.drop(columns=["_mask_in_window"])
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("location", sort=False)["PRECTOTCORR"]
    for w in RAIN_WINDOWS:
        df[f"rain_{w}day"] = g.transform(lambda s, w=w: s.rolling(w, min_periods=w).sum())

    # Antecedent wetness: soil moisture is already in the raw export for every location
    # and every day, and is operationally available at the same T-3 latency.
    for c in SOIL:
        if c in df.columns:
            df[f"{c.lower()}_lag1d"] = df.groupby("location", sort=False)[c].shift(1)

    # Temporal / seasonal encodings.
    df["month"] = df.date.dt.month.astype(np.float32)
    df["doy"] = df.date.dt.dayofyear.astype(np.float32)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365.25)
    df["is_rainy_season"] = ((df["month"] >= 11) | (df["month"] <= 4)).astype(np.float32)

    # Climate indices, lagged by whole months. lag-0 is built for transparency and
    # explicitly never used: a monthly index is only finalised after its month ends.
    df["year_month"] = df.date.dt.to_period("M")
    for path, col in [(C.NINO34_CSV, "nino34_anomaly_degC"), (C.DMI_CSV, "dmi_iod_degC")]:
        idx = pd.read_csv(path, parse_dates=["date"])
        idx["year_month"] = idx.date.dt.to_period("M")
        short = "nino34" if "nino" in col else "dmi"
        df = df.merge(idx[["year_month", col]].rename(columns={col: f"{short}_lag0m_UNSAFE"}),
                      on="year_month", how="left")
        for lag in (1, 3, 6):
            lagged = idx[["year_month", col]].copy()
            lagged["year_month"] = lagged["year_month"] + lag
            df = df.merge(lagged.rename(columns={col: f"{short}_lag{lag}m"}),
                          on="year_month", how="left")
    df = df.drop(columns=["year_month"])
    return df


def add_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    loc = pd.read_csv(C.LOCATIONS_CSV)[["name", "lat", "lon", "coord_status"]]
    return df.merge(loc.rename(columns={"name": "location"}), on="location", how="left")


def split_chronologically(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split by GLOBAL DATE so no location's future can appear in another's past."""
    dates = np.sort(df.date.unique())
    train_cut = dates[int(len(dates) * C.TRAIN_FRAC)]
    val_cut = dates[int(len(dates) * (C.TRAIN_FRAC + C.VAL_FRAC))]
    return {
        "train": df[df.date <= train_cut],
        "validation": df[(df.date > train_cut) & (df.date <= val_cut)],
        "test": df[df.date > val_cut],
    }


def main() -> None:
    C.ensure_out_dirs()
    print("Loading weather ...")
    df = load_weather()

    print("Applying reconciled labels ...")
    df = add_labels(df)

    print("Building target ...")
    df = build_target(df)

    print("Building features ...")
    df = add_features(df)
    df = add_coordinates(df)

    # Drop rows with any missing REQUIRED value. Never impute -- an imputed weather or
    # climate value would be fabricated data.
    before = len(df)
    df = df.dropna(subset=REQUIRED).reset_index(drop=True)
    print(f"  dropped {before - len(df):,} rows missing a required feature "
          f"(rolling warm-up and climate-index edges); {len(df):,} remain")

    splits = split_chronologically(df)
    manifest = {"horizon_days": C.HORIZON_DAYS, "seed": C.SEED, "splits": {}}
    for name, part in splits.items():
        usable = part[part[C.MASK_COL] == 1]
        out = C.PROCESSED_DIR / f"{name}.csv"
        part.to_csv(out, index=False)
        manifest["splits"][name] = {
            "rows": int(len(part)),
            "rows_usable": int(len(usable)),
            "rows_masked": int(len(part) - len(usable)),
            "positives": int(usable[C.TARGET].sum()),
            "positive_rate_usable": round(float(usable[C.TARGET].mean()), 8),
            "date_min": str(part.date.min().date()),
            "date_max": str(part.date.max().date()),
            "locations": int(part.location.nunique()),
        }
        m = manifest["splits"][name]
        print(f"  {name:11s} rows={m['rows']:>7,} usable={m['rows_usable']:>7,} "
              f"masked={m['rows_masked']:>6,} pos={m['positives']:>5} "
              f"rate={m['positive_rate_usable']:.6%} {m['date_min']}->{m['date_max']}")

    manifest["columns"] = sorted(df.columns)
    (C.PROCESSED_DIR / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {C.PROCESSED_DIR}")


if __name__ == "__main__":
    main()
