"""Phases 8, 9, 10, 12, 13 - baselines, feature ablation, model comparison, rolling origin.

THE TEST SET IS LOCKED. Nothing in this module reads test.csv. Every number it produces
comes from training and validation data only. The single final test evaluation lives in
p20_final_evaluation.py and runs once, after the pipeline is frozen.

The scientific question is not "what is the highest ROC-AUC" but:

    does a machine-learning model provide meaningful incremental skill beyond
    seasonality and simple rainfall accumulation?

So two reference baselines are first-class citizens, evaluated identically to every model:

  seasonal_climatology   day-of-year flood frequency learned from the training years
                         only. Uses NO weather at all.
  rain_Nday              a single backward-looking rainfall accumulation, used raw as a
                         score. No fitting beyond its own ordering.

Masked rows (label_usable == 0) are dropped from training and from every evaluation.
They are days where the sources leave the outcome undetermined; scoring against them
would measure agreement with an unknown.

    python ml/pipeline/p10_experiments.py            # fixed-split ablation
    python ml/pipeline/p10_experiments.py --rolling   # add rolling-origin validation
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

WEATHER = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"]
RAIN = ["rain_3day", "rain_7day", "rain_14day", "rain_30day"]
SOIL = ["gwetroot_lag1d", "gwetprof_lag1d", "gwettop_lag1d"]
CLIMATE = ["nino34_lag1m", "dmi_lag1m", "nino34_lag3m", "dmi_lag3m",
           "nino34_lag6m", "dmi_lag6m"]
SEASONAL = ["month_sin", "month_cos", "doy_sin", "doy_cos", "is_rainy_season"]

# A derived column, not present in the CSV: the day-of-year flood frequency learned from
# the training fold only. Including it as a FEATURE is what turns "does the model beat
# climatology" into the sharper question "does weather add anything ON TOP of climatology".
# A model given this column starts from the baseline's own information, so any gain it
# shows is incremental skill by construction, and any failure to gain is decisive.
CLIM_FEATURE = "__climatology__"

# Ablation is cumulative and ordered by the physical case for each group, per Phase 13:
# rainfall accumulation first, then antecedent wetness, then slow climate context, then
# explicit seasonality. lag-0 climate indices are never included.
FEATURE_SETS: dict[str, list[str]] = {
    "A_weather_only": WEATHER,
    "B_plus_rain_accum": WEATHER + RAIN,
    "C_plus_soil_moisture": WEATHER + RAIN + SOIL,
    "D_plus_climate_indices": WEATHER + RAIN + SOIL + CLIMATE,
    "E_plus_seasonal_encoding": WEATHER + RAIN + SOIL + CLIMATE + SEASONAL,
    # The incremental-skill tests. F is the control: climatology alone, fitted as a model
    # rather than used as a raw score, so G/H are compared against a like-for-like fit.
    "F_climatology_only": [CLIM_FEATURE],
    "G_climatology_plus_weather": [CLIM_FEATURE] + WEATHER,
    "H_climatology_plus_weather_rain_soil": [CLIM_FEATURE] + WEATHER + RAIN + SOIL,
}

# Feature sets whose result answers "is there skill beyond the baselines?"
INCREMENTAL_SETS = ("F_climatology_only", "G_climatology_plus_weather",
                    "H_climatology_plus_weather_rain_soil")


def attach_climatology(fit_on: pd.DataFrame, *frames: pd.DataFrame) -> None:
    """Add CLIM_FEATURE in place, learned ONLY from `fit_on`.

    Leakage control: the day-of-year rate is estimated on the training fold and then
    looked up for every other frame. No evaluation row contributes to the climatology it
    is scored against.
    """
    rate = seasonal_climatology_table(fit_on)
    for f in (fit_on,) + frames:
        f[CLIM_FEATURE] = rate[f.date.dt.dayofyear.to_numpy() - 1]


def make_models(seed: int = C.SEED) -> dict:
    m = {
        "LogisticRegression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=seed),
        "DecisionTree": DecisionTreeClassifier(
            max_depth=8, class_weight="balanced", random_state=seed),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=10, n_jobs=-1,
            class_weight="balanced", random_state=seed),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100, max_depth=3, random_state=seed),
    }
    if XGB:
        m["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            eval_metric="logloss", random_state=seed, n_jobs=-1)
    return m


def evaluate(y, pred, proba) -> dict:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    single = len(set(y)) < 2
    # Brier score is only defined for calibrated probabilities. The reference baselines
    # are raw scores (rain_7day is millimetres, up to ~650), so reporting a Brier for
    # them would be meaningless -- it is left as NaN rather than manufactured by
    # rescaling a score that was never a probability.
    is_probability = bool(np.all((proba >= 0.0) & (proba <= 1.0)))
    return {
        "roc_auc": float("nan") if single else roc_auc_score(y, proba),
        "pr_auc": float("nan") if single else average_precision_score(y, proba),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "f1": f1_score(y, pred, zero_division=0),
        "brier": brier_score_loss(y, proba) if is_probability else float("nan"),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "n": int(len(y)), "positives": int(tp + fn),
        "base_rate": float((tp + fn) / len(y)) if len(y) else float("nan"),
    }


def usable(df: pd.DataFrame) -> pd.DataFrame:
    return df[df[C.MASK_COL] == 1]


def load(name: str) -> pd.DataFrame:
    p = C.PROCESSED_DIR / f"{name}.csv"
    if not p.exists():
        raise SystemExit(f"missing {p}; run ml/pipeline/p06_build_dataset.py first")
    return pd.read_csv(p, parse_dates=["date"], low_memory=False)


# ---------------------------------------------------------------------------
# Baselines (Phase 8)
# ---------------------------------------------------------------------------

def seasonal_climatology_table(train: pd.DataFrame, smooth_days: int = 7) -> np.ndarray:
    """Length-366 day-of-year flood frequency, learned on TRAIN only and smoothed
    circularly so 31 Dec and 1 Jan are neighbours. Uses no weather whatsoever."""
    doy = train.date.dt.dayofyear
    rate = train.groupby(doy)[C.TARGET].mean().reindex(range(1, 367)).fillna(0.0).to_numpy()
    k = 2 * smooth_days + 1
    kernel = np.ones(k) / k
    padded = np.concatenate([rate[-smooth_days:], rate, rate[:smooth_days]])
    return np.convolve(padded, kernel, mode="valid")


def seasonal_climatology(train: pd.DataFrame, target: pd.DataFrame,
                         smooth_days: int = 7) -> np.ndarray:
    table = seasonal_climatology_table(train, smooth_days)
    return table[target.date.dt.dayofyear.to_numpy() - 1]


def baseline_scores(train: pd.DataFrame, target: pd.DataFrame) -> dict[str, np.ndarray]:
    out = {"seasonal_climatology": seasonal_climatology(train, target)}
    for c in RAIN:
        if c in target.columns:
            out[f"rainfall_only_{c}"] = target[c].to_numpy(dtype=float)
    # A combined naive rule: is it the rainy season at all.
    if "is_rainy_season" in target.columns:
        out["rainy_season_flag_only"] = target["is_rainy_season"].to_numpy(dtype=float)
    return out


def score_baselines(train: pd.DataFrame, val: pd.DataFrame) -> list[dict]:
    rows = []
    for name, s in baseline_scores(train, val).items():
        # Baselines are scores, not probabilities. Rank metrics are meaningful; a
        # threshold is not, so the median is used purely to fill the confusion matrix
        # and precision/recall for a baseline are reported as indicative only.
        pred = (s >= np.nanmedian(s)).astype(int)
        m = evaluate(val[C.TARGET].to_numpy(), pred, np.nan_to_num(s))
        rows.append({"kind": "baseline", "name": name, "features": "-", "split": "val", **m})
    return rows


# ---------------------------------------------------------------------------
# Fixed-split ablation (Phases 12, 13) - VALIDATION ONLY
# ---------------------------------------------------------------------------

def run_ablation(train: pd.DataFrame, val: pd.DataFrame,
                 only_models: list[str] | None = None) -> pd.DataFrame:
    rows = score_baselines(train, val)
    attach_climatology(train, val)   # learned on train only
    for exp, feats in FEATURE_SETS.items():
        missing = [f for f in feats if f not in train.columns]
        if missing:
            print(f"  skipping {exp}: columns unavailable {missing}")
            continue
        Xtr, ytr = train[feats].to_numpy(float), train[C.TARGET].to_numpy()
        Xva, yva = val[feats].to_numpy(float), val[C.TARGET].to_numpy()
        scaler = RobustScaler().fit(Xtr)          # fit on TRAIN only
        Xtr_s, Xva_s = scaler.transform(Xtr), scaler.transform(Xva)

        for mname, model in make_models().items():
            if only_models and mname not in only_models:
                continue
            t0 = time.time()
            if mname == "XGBoost":
                neg, pos = (ytr == 0).sum(), (ytr == 1).sum()
                model.set_params(scale_pos_weight=neg / max(pos, 1))
                model.fit(Xtr_s, ytr)
            elif mname == "GradientBoosting":
                model.fit(Xtr_s, ytr, sample_weight=compute_sample_weight("balanced", ytr))
            else:
                model.fit(Xtr_s, ytr)
            proba = model.predict_proba(Xva_s)[:, 1]
            m = evaluate(yva, (proba >= 0.5).astype(int), proba)
            rows.append({"kind": "model", "name": mname, "features": exp,
                         "split": "val", "n_features": len(feats),
                         "train_seconds": round(time.time() - t0, 1), **m})
            print(f"  {exp:26s} {mname:20s} roc_auc={m['roc_auc']:.4f} "
                  f"pr_auc={m['pr_auc']:.5f} recall={m['recall']:.3f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Rolling-origin validation (Phase 10)
# ---------------------------------------------------------------------------

def run_rolling(df: pd.DataFrame, feature_sets: list[str], models: list[str],
                first_eval_year: int = 2004, min_positives: int = 5) -> pd.DataFrame:
    """Walk-forward: train on everything strictly before year Y, evaluate on year Y.
    A fold is skipped, and said to be skipped, when year Y has too few positives for a
    rank metric to mean anything."""
    rows = []
    years = sorted(y for y in df.date.dt.year.unique() if y >= first_eval_year)
    for y in years:
        tr = df[df.date.dt.year < y]
        ev = df[df.date.dt.year == y]
        if len(tr) == 0 or ev[C.TARGET].sum() < min_positives:
            rows.append({"fold_year": y, "status": "skipped",
                         "reason": f"{int(ev[C.TARGET].sum())} positives < {min_positives}",
                         "positives": int(ev[C.TARGET].sum())})
            continue

        tr, ev = tr.copy(), ev.copy()
        base = baseline_scores(tr, ev)
        for bname, s in base.items():
            m = evaluate(ev[C.TARGET].to_numpy(), (s >= np.nanmedian(s)).astype(int),
                         np.nan_to_num(s))
            rows.append({"fold_year": y, "status": "ok", "kind": "baseline",
                         "name": bname, "features": "-", **m})

        # Climatology learned on this fold's training years only.
        attach_climatology(tr, ev)

        for exp in feature_sets:
            fs = FEATURE_SETS[exp]
            Xtr, ytr = tr[fs].to_numpy(float), tr[C.TARGET].to_numpy()
            Xev, yev = ev[fs].to_numpy(float), ev[C.TARGET].to_numpy()
            scaler = RobustScaler().fit(Xtr)
            Xtr_s, Xev_s = scaler.transform(Xtr), scaler.transform(Xev)
            for mname, model in make_models().items():
                if mname not in models:
                    continue
                if mname == "XGBoost":
                    neg, pos = (ytr == 0).sum(), (ytr == 1).sum()
                    model.set_params(scale_pos_weight=neg / max(pos, 1))
                    model.fit(Xtr_s, ytr)
                elif mname == "GradientBoosting":
                    model.fit(Xtr_s, ytr,
                              sample_weight=compute_sample_weight("balanced", ytr))
                else:
                    model.fit(Xtr_s, ytr)
                proba = model.predict_proba(Xev_s)[:, 1]
                m = evaluate(yev, (proba >= 0.5).astype(int), proba)
                rows.append({"fold_year": y, "status": "ok", "kind": "model",
                             "name": mname, "features": exp, **m})
        print(f"  fold {y}: pos={int(ev[C.TARGET].sum()):>4} train_rows={len(tr):>7,}",
              flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rolling", action="store_true", help="also run rolling-origin validation")
    ap.add_argument("--rolling-features",
                    default="F_climatology_only,G_climatology_plus_weather,"
                            "H_climatology_plus_weather_rain_soil",
                    help="comma-separated feature-set names to roll")
    ap.add_argument("--models", default=None,
                    help="comma-separated model names to restrict the fixed-split run")
    args = ap.parse_args()

    C.ensure_out_dirs()
    train, val = usable(load("train")), usable(load("validation"))
    print(f"train usable={len(train):,} pos={int(train[C.TARGET].sum())} "
          f"({train[C.TARGET].mean():.4%})")
    print(f"val   usable={len(val):,} pos={int(val[C.TARGET].sum())} "
          f"({val[C.TARGET].mean():.4%})")
    print("TEST SET IS LOCKED - not read by this script.\n")

    print("Fixed-split ablation (validation only):")
    res = run_ablation(train, val,
                       only_models=[m.strip() for m in args.models.split(",")]
                       if args.models else None)
    out = C.REPORTS_DIR / "validation_ablation.csv"
    res.to_csv(out, index=False)
    print(f"\nWrote {out}")

    print("\n--- validation ranking by PR-AUC (the right primary metric at this base rate) ---")
    r = res.dropna(subset=["pr_auc"]).sort_values("pr_auc", ascending=False)
    print(r[["kind", "name", "features", "roc_auc", "pr_auc", "recall", "positives"]]
          .head(14).to_string(index=False))

    # ---- the incremental-skill verdict on the fixed split ----
    print("\n--- INCREMENTAL SKILL: does weather add anything ON TOP of climatology? ---")
    inc = res[res.features.isin(INCREMENTAL_SETS)].dropna(subset=["pr_auc"])
    if len(inc):
        ctrl = inc[inc.features == "F_climatology_only"]
        ctrl_pr = float(ctrl.pr_auc.max()) if len(ctrl) else float("nan")
        print(f"  control  F_climatology_only        best PR-AUC = {ctrl_pr:.6f}")
        for fs in ("G_climatology_plus_weather", "H_climatology_plus_weather_rain_soil"):
            sub = inc[inc.features == fs]
            if not len(sub):
                continue
            best = sub.loc[sub.pr_auc.idxmax()]
            delta = (best.pr_auc / ctrl_pr - 1) * 100 if ctrl_pr else float("nan")
            print(f"  {fs:40s} best PR-AUC = {best.pr_auc:.6f} "
                  f"({delta:+.1f}% vs control, {best['name']})")

    if args.rolling:
        sets = [s.strip() for s in args.rolling_features.split(",")]
        full = pd.concat([usable(load("train")), usable(load("validation"))],
                         ignore_index=True)
        print(f"\nRolling-origin validation on {sets}, train+validation years only.")
        print("Only fast model families are used here; 20+ folds x slow ensembles is "
              "hours of compute for no extra inferential value.")
        roll = run_rolling(full, sets,
                           models=["LogisticRegression", "DecisionTree", "XGBoost"])
        rout = C.REPORTS_DIR / "rolling_origin_validation.csv"
        roll.to_csv(rout, index=False)
        print(f"Wrote {rout}")
        ok = roll[roll.status == "ok"]
        if len(ok):
            summ = (ok.groupby(["kind", "name", "features"])["pr_auc"]
                    .agg(folds="count", mean="mean", std="std", min="min", max="max")
                    .sort_values("mean", ascending=False))
            print("\n--- rolling-origin PR-AUC distribution (primary metric) ---")
            print(summ.round(6).to_string())

            # Per-fold head-to-head: how often does the best model beat the baseline?
            base = ok[ok.kind == "baseline"].groupby("fold_year").pr_auc.max()
            wins = {}
            for (nm, fs), g in ok[ok.kind == "model"].groupby(["name", "features"]):
                s = g.set_index("fold_year").pr_auc
                common = s.index.intersection(base.index)
                if len(common):
                    wins[f"{nm} / {fs}"] = {
                        "folds": int(len(common)),
                        "folds_beating_baseline": int((s[common] > base[common]).sum()),
                        "win_rate": round(float((s[common] > base[common]).mean()), 3),
                        "mean_pr_auc_ratio": round(
                            float((s[common] / base[common]).mean()), 3),
                    }
            print("\n--- per-fold head-to-head vs the best baseline in that fold ---")
            for k, v in sorted(wins.items(), key=lambda kv: -kv[1]["win_rate"]):
                print(f"  {k:46s} beat baseline in {v['folds_beating_baseline']:>2}/"
                      f"{v['folds']:>2} folds (win rate {v['win_rate']:.2f}, "
                      f"mean ratio {v['mean_pr_auc_ratio']})")
            # summ is indexed by a (kind, name, features) tuple, which json cannot use
            # as a key -- flatten it to a readable string first.
            dist = {" / ".join(map(str, k)): v
                    for k, v in summ.round(6).to_dict(orient="index").items()}
            (C.REPORTS_DIR / "rolling_origin_summary.json").write_text(
                json.dumps({"distribution": dist, "head_to_head": wins},
                           indent=2, default=str),
                encoding="utf-8")


if __name__ == "__main__":
    main()
