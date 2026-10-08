"""Stage 3, step 3 — baselines and models, every horizon, rolling-origin validation.

WHY ROLLING-ORIGIN AND NOT A FIXED SPLIT
A 70/15/15 chronological split of this data puts 82 positives in train, 0 in validation
and 9 in test — validation would contain no positive example at all, so nothing could be
selected, calibrated or thresholded on it. Leave-one-year-out gives a distribution across
the years that actually contain events, which is the only honest design at this density.

Each fold: train on every year strictly before Y, evaluate on year Y. A fold is skipped,
and reported as skipped, when year Y has too few positives for a rank metric to mean
anything.

BASELINES ARE FIRST-CLASS (§24). The question is not "is the model better than nothing"
but "does it beat seasonal climatology and a rainfall rule", computed per fold from that
fold's training years only.

Masked rows (usable_h == 0) are dropped from training and from every evaluation.

    python ml/stage3/s3_experiments.py --horizons 7
    python ml/stage3/s3_experiments.py                # all horizons
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score, brier_score_loss, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.preprocessing import RobustScaler  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402
from sklearn.utils.class_weight import compute_sample_weight  # noqa: E402

from ml import config as C  # noqa: E402

try:
    from xgboost import XGBClassifier
    XGB = True
except ImportError:  # pragma: no cover
    XGB = False

MIN_POS_PER_FOLD = 5

RAIN = ["chirps_sum_1d", "chirps_sum_3d", "chirps_sum_7d", "chirps_sum_14d",
        "chirps_sum_30d", "chirps_max_7d", "chirps_max_30d", "wet_days_30d",
        "chirps_anom_7d", "chirps_anom_30d"]
WEATHER = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"]
SEASON = ["doy_sin", "doy_cos", "is_wet_season"]
SOIL = ["gwettop_lag1", "gwetroot_lag1", "gwetprof_lag1",
        "gwettop_mean_7d", "gwetroot_mean_7d", "gwetprof_mean_7d"]
TERRAIN = ["elev_point_m", "slope_point_deg", "elev_district_mean_m",
           "elev_district_std_m", "slope_district_mean_deg",
           "flat_fraction_slope_lt_0.5deg",
           "dist_point_to_river_upland_ge_100km2_km",
           "upland_km2_of_nearest_river_ge_100km2"]
LANDCOVER = ["pct_tree_cover", "pct_grassland", "pct_cropland", "pct_built_up",
             "pct_permanent_water", "pct_herbaceous_wetland"]
SURFACE = ["pct_ever_water", "pct_intermittent_water_1_to_74",
           "pct_permanent_water_ge_75", "mean_occurrence_pct"]
CLIMATE = ["oni_lag2m", "nino34_lag1m", "dmi_lag1m"]

# §18. Cumulative, ordered by the physical case for each group.
FEATURE_SETS = {
    "A_weather_rain": WEATHER + RAIN + SEASON,
    "B_plus_static_env": WEATHER + RAIN + SEASON + TERRAIN + LANDCOVER + SURFACE,
    "C_plus_hydrology": WEATHER + RAIN + SEASON + SOIL,
    "D_full": WEATHER + RAIN + SEASON + SOIL + TERRAIN + LANDCOVER + SURFACE + CLIMATE,
}


def make_models(seed: int = C.SEED) -> dict:
    m = {
        "LogisticRegression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=seed),
        "DecisionTree": DecisionTreeClassifier(
            max_depth=8, class_weight="balanced", random_state=seed),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=12, n_jobs=-1,
            class_weight="balanced", random_state=seed),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100, max_depth=3, random_state=seed),
    }
    if XGB:
        m["XGBoost"] = XGBClassifier(
            n_estimators=120, max_depth=5, learning_rate=0.1,
            eval_metric="logloss", random_state=seed, n_jobs=-1)
    return m


def evaluate(y, pred, proba) -> dict:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    single = len(set(y)) < 2
    prob_like = bool(np.all((proba >= 0) & (proba <= 1)))
    n = len(y)
    return {
        # flood detection
        "pr_auc": float("nan") if single else average_precision_score(y, proba),
        "roc_auc": float("nan") if single else roc_auc_score(y, proba),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        # no-flood detection (§25)
        "specificity": tn / (tn + fp) if (tn + fp) else float("nan"),
        "npv": tn / (tn + fn) if (tn + fn) else float("nan"),
        "fpr": fp / (fp + tn) if (fp + tn) else float("nan"),
        "balanced_accuracy": 0.5 * ((tp / (tp + fn) if (tp + fn) else 0)
                                    + (tn / (tn + fp) if (tn + fp) else 0)),
        # probability quality
        "brier": brier_score_loss(y, proba) if prob_like else float("nan"),
        # counts
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "n": int(n), "positives": int(tp + fn),
        "prevalence": float((tp + fn) / n) if n else float("nan"),
        "accuracy": float((tp + tn) / n) if n else float("nan"),
    }


def climatology(train: pd.DataFrame, target: pd.DataFrame, tcol: str,
                smooth: int = 7) -> np.ndarray:
    """Day-of-year event frequency from the fold's TRAINING years only. No weather."""
    doy = train.date.dt.dayofyear
    rate = train.groupby(doy)[tcol].mean().reindex(range(1, 367)).fillna(0.0).to_numpy()
    k = 2 * smooth + 1
    padded = np.concatenate([rate[-smooth:], rate, rate[:smooth]])
    sm = np.convolve(padded, np.ones(k) / k, mode="valid")
    return sm[target.date.dt.dayofyear.to_numpy() - 1]


def baselines(train: pd.DataFrame, ev: pd.DataFrame, tcol: str) -> dict:
    out = {"seasonal_climatology": climatology(train, ev, tcol)}
    for c in ("chirps_sum_7d", "chirps_sum_14d", "chirps_sum_30d"):
        if c in ev.columns:
            out[f"rainfall_rule_{c}"] = ev[c].to_numpy(float)
    # District historical event frequency, training years only (§24).
    freq = train.groupby("location_id")[tcol].mean()
    out["district_event_frequency"] = ev.location_id.map(freq).fillna(0.0).to_numpy()
    return out


def run(df: pd.DataFrame, h: int, feature_sets: list[str], models: list[str]) -> list[dict]:
    tcol, ucol = f"target_h{h}", f"usable_h{h}"
    d = df[df[ucol] == 1].copy()
    rows = []
    years = sorted(d.date.dt.year.unique())
    for y in years:
        tr, ev = d[d.date.dt.year < y], d[d.date.dt.year == y]
        pos = int(ev[tcol].sum())
        if len(tr) == 0 or pos < MIN_POS_PER_FOLD or tr[tcol].sum() < MIN_POS_PER_FOLD:
            rows.append({"horizon": h, "fold_year": y, "status": "skipped",
                         "positives": pos,
                         "reason": f"{pos} eval positives / {int(tr[tcol].sum())} train positives"})
            continue

        for bname, s in baselines(tr, ev, tcol).items():
            m = evaluate(ev[tcol].to_numpy(), (s >= np.nanmedian(s)).astype(int),
                         np.nan_to_num(s))
            rows.append({"horizon": h, "fold_year": y, "status": "ok", "kind": "baseline",
                         "name": bname, "features": "-", **m})

        for fs in feature_sets:
            cols = [c for c in FEATURE_SETS[fs] if c in d.columns]
            Xtr = tr[cols].to_numpy(np.float32)
            ytr = tr[tcol].to_numpy()
            Xev, yev = ev[cols].to_numpy(np.float32), ev[tcol].to_numpy()
            sc = RobustScaler().fit(Xtr)           # fitted on the fold's train only
            Xtr_s, Xev_s = sc.transform(Xtr), sc.transform(Xev)
            for mname, model in make_models().items():
                if mname not in models:
                    continue
                t0 = time.time()
                if mname == "XGBoost":
                    neg, p = (ytr == 0).sum(), (ytr == 1).sum()
                    model.set_params(scale_pos_weight=neg / max(p, 1))
                    model.fit(Xtr_s, ytr)
                elif mname == "GradientBoosting":
                    model.fit(Xtr_s, ytr,
                              sample_weight=compute_sample_weight("balanced", ytr))
                else:
                    model.fit(Xtr_s, ytr)
                proba = model.predict_proba(Xev_s)[:, 1]
                m = evaluate(yev, (proba >= 0.5).astype(int), proba)
                rows.append({"horizon": h, "fold_year": y, "status": "ok", "kind": "model",
                             "name": mname, "features": fs,
                             "train_seconds": round(time.time() - t0, 1), **m})
        print(f"  H+{h} fold {y}: eval_pos={pos:>4} train_rows={len(tr):>7,}", flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", default=",".join(str(h) for h in C.S3_HORIZONS))
    ap.add_argument("--features", default=",".join(FEATURE_SETS))
    ap.add_argument("--models", default="LogisticRegression,DecisionTree,XGBoost")
    args = ap.parse_args()

    C.ensure_s3_dirs()
    horizons = [int(x) for x in args.horizons.split(",")]
    fsets = [f.strip() for f in args.features.split(",")]
    models = [m.strip() for m in args.models.split(",")]

    # Read only the columns these feature sets need, as float32. The full frame is ~84
    # float64 columns over 970k rows, so every per-fold slice copied ~600 MB and that
    # dominated runtime far more than the model fits. Engineering only: no feature,
    # split, label or metric changes.
    import pyarrow.parquet as pq
    path = C.S3_OUT_PROCESSED / "forecasting_dataset.parquet"
    needed = {"location_id", "date"}
    for fs in fsets:
        needed |= set(FEATURE_SETS[fs])
    for h in horizons:
        needed |= {f"target_h{h}", f"usable_h{h}"}
    avail = set(pq.ParquetFile(path).schema.names)
    df = pd.read_parquet(path, columns=sorted(needed & avail))
    for c in df.columns:
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    print(f"dataset {len(df):,} rows, {df.location_id.nunique()} districts, "
          f"{df.date.min().date()} -> {df.date.max().date()}")
    print(f"  {len(df.columns)} of {len(avail)} columns, float32, "
          f"{df.memory_usage(deep=True).sum() / 1e6:.0f} MB")
    print(f"XGBoost available: {XGB}")


    allrows = []
    out = C.S3_OUT_REPORTS / "rolling_origin_results.csv"
    for h in horizons:
        print(f"--- H+{h} ---")
        allrows += run(df, h, fsets, models)
        # Checkpoint after every horizon. The first full sweep held everything in memory
        # until the very end, so a crash or timeout hours in would have lost it all.
        pd.DataFrame(allrows).to_csv(out, index=False)
        print(f"  [checkpoint] H+{h} saved ({len(allrows)} rows)", flush=True)

    res = pd.DataFrame(allrows)
    print(f"Wrote {out}  ({len(res)} rows)")

    ok = res[res.status == "ok"].dropna(subset=["pr_auc"])
    if not len(ok):
        print("no evaluable folds")
        return

    print("\n=== per-horizon: mean PR-AUC across folds, model vs best baseline ===")
    summary = {}
    for h in horizons:
        hh = ok[ok.horizon == h]
        if not len(hh):
            print(f"  H+{h}: no evaluable folds"); continue
        base = hh[hh.kind == "baseline"].groupby("fold_year").pr_auc.max()
        best_b = hh[hh.kind == "baseline"].groupby("name").pr_auc.mean().sort_values(ascending=False)
        rows = []
        for (nm, fs), g in hh[hh.kind == "model"].groupby(["name", "features"]):
            s = g.set_index("fold_year").pr_auc
            common = s.index.intersection(base.index)
            if not len(common):
                continue
            ratio = s[common] / base[common]
            rows.append({"model": nm, "features": fs, "folds": len(common),
                         "mean_pr_auc": s[common].mean(),
                         "wins": int((s[common] > base[common]).sum()),
                         "win_rate": round(float((s[common] > base[common]).mean()), 3),
                         "median_ratio": round(float(ratio.median()), 3),
                         "mean_recall": g.set_index("fold_year").recall[common].mean(),
                         "mean_specificity": g.set_index("fold_year").specificity[common].mean()})
        t = pd.DataFrame(rows).sort_values("win_rate", ascending=False)
        summary[f"h{h}"] = {
            "folds": int(base.size),
            "best_baseline": str(best_b.index[0]) if len(best_b) else None,
            "best_baseline_mean_pr_auc": float(best_b.iloc[0]) if len(best_b) else None,
            "models": t.to_dict(orient="records"),
        }
        print(f"\n  H+{h}  ({base.size} folds)   best baseline: {best_b.index[0]} "
              f"(mean PR-AUC {best_b.iloc[0]:.5f})")
        print(t.head(6).to_string(index=False))

    (C.S3_OUT_REPORTS / "rolling_origin_summary.json").write_text(
        json.dumps(summary, indent=2, default=float), encoding="utf-8")
    print(f"\nWrote {C.S3_OUT_REPORTS / 'rolling_origin_summary.json'}")


if __name__ == "__main__":
    main()
