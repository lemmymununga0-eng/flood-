"""Stage 3, step 6 — probability quality (§27).

A model that outputs numbers between 0 and 1 is not thereby producing probabilities.
This asks whether they mean anything: do days scored ~0.8 flood substantially more often
than days scored ~0.2?

Method, and why it is shaped this way:

  * Calibration is assessed FOLD-WISE under the same rolling-origin design as the
    experiments. Fitting a calibrator on the whole series and then reporting a reliability
    curve on it would be fitting and grading on the same data.
  * For each fold, the model is trained on prior years and a sigmoid calibrator is fitted
    on a held-out slice of those SAME training years — never on the evaluation year. The
    curve is then drawn on the untouched evaluation year.
  * Brier is reported raw and calibrated. At a base rate near 0.06% a model that simply
    predicts the base rate everywhere gets an excellent Brier, so Brier alone is
    reported alongside a reference Brier for that constant predictor, otherwise the
    number flatters.

    python ml/stage3/s6_calibration.py --horizon 7
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.frozen import FrozenEstimator  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402
from sklearn.preprocessing import RobustScaler  # noqa: E402

from ml import config as C  # noqa: E402
from ml.stage3.s3_experiments import FEATURE_SETS, MIN_POS_PER_FOLD, make_models  # noqa: E402

N_BINS = 10


def reliability(y: np.ndarray, p: np.ndarray, bins: int = N_BINS) -> list[dict]:
    """Quantile bins — equal-width bins are useless when almost every score is tiny."""
    try:
        edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
        if len(edges) < 3:
            return []
        idx = np.clip(np.digitize(p, edges[1:-1]), 0, len(edges) - 2)
    except Exception:
        return []
    out = []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() < 20:
            continue
        out.append({"bin": b, "n": int(m.sum()),
                    "mean_predicted": round(float(p[m].mean()), 6),
                    "observed_rate": round(float(y[m].mean()), 6)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=C.S3_PRIMARY_HORIZON)
    ap.add_argument("--features", default="A_weather_rain")
    ap.add_argument("--model", default="LogisticRegression")
    args = ap.parse_args()

    C.ensure_s3_dirs()
    h, fs = args.horizon, args.features
    tcol, ucol = f"target_h{h}", f"usable_h{h}"
    cols = sorted({"location_id", "date", tcol, ucol} | set(FEATURE_SETS[fs]))
    import pyarrow.parquet as pq
    path = C.S3_OUT_PROCESSED / "forecasting_dataset.parquet"
    avail = set(pq.ParquetFile(path).schema.names)
    df = pd.read_parquet(path, columns=sorted(set(cols) & avail))
    for c in df.columns:
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    d = df[df[ucol] == 1]
    feats = [c for c in FEATURE_SETS[fs] if c in d.columns]

    print(f"calibration: H+{h}, {args.model} on {fs} ({len(feats)} features)\n")
    rows, curves = [], {}
    for y in sorted(d.date.dt.year.unique()):
        tr, ev = d[d.date.dt.year < y], d[d.date.dt.year == y]
        if len(tr) == 0 or ev[tcol].sum() < MIN_POS_PER_FOLD or tr[tcol].sum() < MIN_POS_PER_FOLD:
            continue
        # Hold out the last training year to fit the calibrator — never the eval year.
        tyears = sorted(tr.date.dt.year.unique())
        if len(tyears) < 2:
            continue
        cal_year = tyears[-1]
        fit = tr[tr.date.dt.year < cal_year]
        cal = tr[tr.date.dt.year == cal_year]
        if fit[tcol].sum() < MIN_POS_PER_FOLD or cal[tcol].sum() < 1:
            continue

        sc = RobustScaler().fit(fit[feats].to_numpy(np.float32))
        model = make_models()[args.model]
        model.fit(sc.transform(fit[feats].to_numpy(np.float32)), fit[tcol].to_numpy())

        Xcal = sc.transform(cal[feats].to_numpy(np.float32))
        calibrator = CalibratedClassifierCV(
            FrozenEstimator(model), method="sigmoid").fit(Xcal, cal[tcol].to_numpy())

        Xev = sc.transform(ev[feats].to_numpy(np.float32))
        yev = ev[tcol].to_numpy()
        raw = model.predict_proba(Xev)[:, 1]
        cp = calibrator.predict_proba(Xev)[:, 1]
        base_rate = float(yev.mean())
        const = np.full_like(cp, base_rate)

        rows.append({
            "fold_year": int(y), "n": int(len(yev)), "positives": int(yev.sum()),
            "base_rate": round(base_rate, 6),
            "brier_raw": round(float(brier_score_loss(yev, raw)), 6),
            "brier_calibrated": round(float(brier_score_loss(yev, cp)), 6),
            "brier_constant_baserate": round(float(brier_score_loss(yev, const)), 6),
            "roc_auc_raw": round(float(roc_auc_score(yev, raw)), 4) if len(set(yev)) > 1 else None,
            "roc_auc_calibrated": round(float(roc_auc_score(yev, cp)), 4) if len(set(yev)) > 1 else None,
            "mean_predicted_calibrated": round(float(cp.mean()), 6),
        })
        curves[str(y)] = reliability(yev, cp)
        r = rows[-1]
        print(f"  {y}  n={r['n']:>7,} pos={r['positives']:>4} base={r['base_rate']:.5f} "
              f"| Brier raw {r['brier_raw']:.5f} cal {r['brier_calibrated']:.5f} "
              f"const {r['brier_constant_baserate']:.5f} "
              f"| ROC {r['roc_auc_raw']} -> {r['roc_auc_calibrated']}")

    if not rows:
        print("no evaluable folds"); return
    t = pd.DataFrame(rows)
    beats_const = int((t.brier_calibrated < t.brier_constant_baserate).sum())
    print(f"\nfolds where the calibrated model beats a constant base-rate predictor "
          f"on Brier: {beats_const}/{len(t)}")
    print("  (a constant predictor is the bar that matters at this prevalence — "
          "Brier alone flatters any model that simply predicts 'almost never')")

    out = {"horizon": h, "features": fs, "model": args.model,
           "folds": rows, "reliability_curves": curves,
           "folds_beating_constant_baserate": beats_const, "n_folds": int(len(t)),
           "mean_brier_raw": round(float(t.brier_raw.mean()), 6),
           "mean_brier_calibrated": round(float(t.brier_calibrated.mean()), 6),
           "mean_brier_constant": round(float(t.brier_constant_baserate.mean()), 6)}
    p = C.S3_OUT_REPORTS / f"calibration_h{h}.json"
    p.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(f"\nWrote {p}")


if __name__ == "__main__":
    main()
