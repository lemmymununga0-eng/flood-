"""Stage 3, step 7 — control experiments: does the harness itself tell the truth?

A skill number means nothing unless the machinery that produced it can (a) report NO skill
when there is none and (b) report skill when there is. Two controls, run through the very
same fold loop, features, scaler and metrics as the real experiment:

  NEGATIVE CONTROL  Evaluation labels are randomly permuted within each fold. Any feature
                    is now unrelated to the target by construction, so PR-AUC must fall to
                    roughly the base rate and ROC-AUC to ~0.5. If it does not, something
                    in the pipeline is manufacturing skill (leakage, a metric bug, or
                    row-order dependence).

  POSITIVE CONTROL  The true target is injected as an extra feature (an obvious leak).
                    The harness must score near-perfect. If it does not, the harness is
                    insensitive and its "no skill" verdicts mean nothing.

Both must pass before any real result is believed.

    python ml/stage3/s7_controls.py --horizon 7
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402
from sklearn.preprocessing import RobustScaler  # noqa: E402

from ml import config as C  # noqa: E402
from ml.stage3.s3_experiments import FEATURE_SETS, MIN_POS_PER_FOLD  # noqa: E402

N_PERMUTATIONS = 5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=C.S3_PRIMARY_HORIZON)
    ap.add_argument("--features", default="A_weather_rain")
    args = ap.parse_args()

    C.ensure_s3_dirs()
    h, fs = args.horizon, args.features
    tcol, ucol = f"target_h{h}", f"usable_h{h}"
    import pyarrow.parquet as pq
    path = C.S3_OUT_PROCESSED / "forecasting_dataset.parquet"
    avail = set(pq.ParquetFile(path).schema.names)
    cols = sorted({"location_id", "date", tcol, ucol} | set(FEATURE_SETS[fs]))
    df = pd.read_parquet(path, columns=sorted(set(cols) & avail))
    for c in df.columns:
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
    d = df[df[ucol] == 1]
    feats = [c for c in FEATURE_SETS[fs] if c in d.columns]
    rng = np.random.default_rng(C.SEED)

    neg, pos, real = [], [], []
    for y in sorted(d.date.dt.year.unique()):
        tr, ev = d[d.date.dt.year < y], d[d.date.dt.year == y]
        if len(tr) == 0 or ev[tcol].sum() < MIN_POS_PER_FOLD or tr[tcol].sum() < MIN_POS_PER_FOLD:
            continue
        ytr, yev = tr[tcol].to_numpy(), ev[tcol].to_numpy()
        base = float(yev.mean())

        def fit_score(Xtr, Xev, ytr_, yev_):
            sc = RobustScaler().fit(Xtr)
            m = LogisticRegression(max_iter=2000, class_weight="balanced",
                                   random_state=C.SEED)
            m.fit(sc.transform(Xtr), ytr_)
            p = m.predict_proba(sc.transform(Xev))[:, 1]
            return (average_precision_score(yev_, p), roc_auc_score(yev_, p))

        Xtr = tr[feats].to_numpy(np.float32)
        Xev = ev[feats].to_numpy(np.float32)

        # real (same model, for direct comparison to the controls)
        ap_r, roc_r = fit_score(Xtr, Xev, ytr, yev)
        real.append({"fold": int(y), "base": base, "pr_auc": ap_r, "roc_auc": roc_r})

        # NEGATIVE: permute BOTH the training and evaluation labels. Permuting only the
        # evaluation labels would leave a model trained on real structure scored against
        # noise, which proves little. Permuting both asks: with no signal anywhere, does
        # the pipeline still report some?
        aps, rocs = [], []
        for _ in range(N_PERMUTATIONS):
            a, b = fit_score(Xtr, Xev, rng.permutation(ytr), rng.permutation(yev))
            aps.append(a); rocs.append(b)
        neg.append({"fold": int(y), "base": base,
                    "pr_auc": float(np.mean(aps)), "roc_auc": float(np.mean(rocs))})

        # POSITIVE: inject the true target as a feature. Training sees the true training
        # target, evaluation sees the true evaluation target — a blatant leak.
        a, b = fit_score(np.c_[Xtr, ytr.astype(np.float32)],
                         np.c_[Xev, yev.astype(np.float32)], ytr, yev)
        pos.append({"fold": int(y), "base": base, "pr_auc": a, "roc_auc": b})
        print(f"  fold {y}: base={base:.5f} | real PR-AUC {ap_r:.5f} "
              f"| NEG ctrl {neg[-1]['pr_auc']:.5f} | POS ctrl {a:.4f}", flush=True)

    R, N, P = (pd.DataFrame(x) for x in (real, neg, pos))
    summary = {
        "horizon": h, "features": fs, "folds": int(len(R)),
        "mean_base_rate": round(float(R.base.mean()), 6),
        "real": {"pr_auc": round(float(R.pr_auc.mean()), 6),
                 "roc_auc": round(float(R.roc_auc.mean()), 4)},
        "negative_control": {"pr_auc": round(float(N.pr_auc.mean()), 6),
                             "roc_auc": round(float(N.roc_auc.mean()), 4)},
        "positive_control": {"pr_auc": round(float(P.pr_auc.mean()), 4),
                             "roc_auc": round(float(P.roc_auc.mean()), 4)},
    }
    # Tolerances are deliberately loose: with ~20-50 positives per fold the permuted PR-AUC
    # wanders well above the base rate by chance, so the test is "no meaningful skill",
    # not "exactly the base rate".
    neg_ok = (summary["negative_control"]["roc_auc"] < 0.60
              and summary["negative_control"]["pr_auc"] < 5 * summary["mean_base_rate"])
    pos_ok = summary["positive_control"]["roc_auc"] > 0.95
    summary["negative_control_passed"] = bool(neg_ok)
    summary["positive_control_passed"] = bool(pos_ok)
    summary["harness_trustworthy"] = bool(neg_ok and pos_ok)

    print("\n" + "=" * 70)
    print(f"base rate (mean)         {summary['mean_base_rate']}")
    print(f"REAL                     PR-AUC {summary['real']['pr_auc']}  ROC {summary['real']['roc_auc']}")
    print(f"NEGATIVE (shuffled)      PR-AUC {summary['negative_control']['pr_auc']}  "
          f"ROC {summary['negative_control']['roc_auc']}   -> {'PASS' if neg_ok else 'FAIL'}")
    print(f"POSITIVE (leaked target) PR-AUC {summary['positive_control']['pr_auc']}  "
          f"ROC {summary['positive_control']['roc_auc']}   -> {'PASS' if pos_ok else 'FAIL'}")
    print(f"HARNESS TRUSTWORTHY: {summary['harness_trustworthy']}")
    print("=" * 70)

    p = C.S3_OUT_REPORTS / f"controls_h{h}.json"
    p.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {p}")


if __name__ == "__main__":
    main()
