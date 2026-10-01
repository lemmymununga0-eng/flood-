"""Phase 1 - preserve CURRENT_RESEARCH_BASELINE.

Records a cryptographic inventory of every artifact, dataset and metric the existing
research produced, so that (a) the baseline stays reproducible and (b) any later claim
that "nothing was overwritten" is verifiable rather than asserted.

This script WRITES NOTHING outside ml/baseline/. It never touches the baseline itself.

    python ml/pipeline/p01_freeze_baseline.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402


def sha256(path: pathlib.Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def stat_entry(path: pathlib.Path, *, hash_it: bool = True) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False}
    e = {
        "path": str(path.relative_to(path.anchor)),
        "exists": True,
        "bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    }
    # Hash everything except the very large raw inputs, where size+mtime suffices
    # and a full hash would cost minutes for no extra assurance.
    if hash_it and path.stat().st_size < 200 * 1024 * 1024:
        e["sha256"] = sha256(path)
    return e


def main() -> None:
    C.ensure_out_dirs()
    inv: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Frozen inventory of CURRENT_RESEARCH_BASELINE. The corrected pipeline "
            "writes only to OUT_ROOT and never modifies anything listed here."
        ),
        "data_root": str(C.DATA_ROOT),
        "inputs": {},
        "baseline_artifacts": {},
        "baseline_processed": {},
        "baseline_reports": {},
        "baseline_metrics": {},
        "target_definition": {},
        "splits": {},
    }

    # ---- raw inputs ----
    for name, p in [
        ("locations", C.LOCATIONS_CSV), ("weather_nasa_power", C.WEATHER_CSV),
        ("events_desinventar", C.DESINVENTAR_CSV), ("events_dfo", C.DFO_CSV),
        ("events_curated_log", C.CURATED_EVENTS_CSV),
        ("climate_nino34", C.NINO34_CSV), ("climate_dmi", C.DMI_CSV),
        ("glofas_discharge", C.GLOFAS_CSV),
        ("master_dataset", C.DATA_ROOT / "flood_master_dataset.csv"),
    ]:
        inv["inputs"][name] = stat_entry(p)

    # ---- production model artifacts, both copies ----
    for label, root in [
        ("research_bundle", C.BASELINE_MODEL_DIR),
        ("backend_deployed", C.REPO_ROOT / "backend" / "ml_artifacts" / "flood_risk_lr_v1"),
    ]:
        inv["baseline_artifacts"][label] = {
            f.name: stat_entry(f) for f in sorted(root.glob("*")) if f.is_file()
        } if root.exists() else {"_missing": str(root)}

    # ---- processed splits ----
    for name in ("train.csv", "validation.csv", "test.csv"):
        inv["baseline_processed"][name] = stat_entry(C.BASELINE_PROCESSED_DIR / name, hash_it=False)

    # ---- reports ----
    if C.BASELINE_REPORTS_DIR.exists():
        for f in sorted(C.BASELINE_REPORTS_DIR.glob("*")):
            if f.is_file():
                inv["baseline_reports"][f.name] = stat_entry(f)

    # ---- the measured baseline result, read from its own results file ----
    res_path = C.BASELINE_REPORTS_DIR / "experiment_results.csv"
    if res_path.exists():
        r = pd.read_csv(res_path)
        sel = r[(r.experiment == "A_weather_only") & (r.model == "LogisticRegression")]
        inv["baseline_metrics"] = {
            "n_runs": int(len(r)),
            "selected_model": "LogisticRegression / A_weather_only",
            "by_split": {
                row.split: {
                    "roc_auc": float(row.roc_auc), "pr_auc": float(row.pr_auc),
                    "precision": float(row.precision), "recall": float(row.recall),
                    "f1": float(row.f1), "brier": float(row.brier),
                    "tp": int(row.true_positive), "fp": int(row.false_positive),
                    "tn": int(row.true_negative), "fn": int(row.false_negative),
                }
                for row in sel.itertuples()
            },
            "validation_ranking_top3": [
                {"experiment": t.experiment, "model": t.model, "roc_auc": float(t.roc_auc)}
                for t in r[r.split == "val"].nlargest(3, "roc_auc").itertuples()
            ],
            "selection_contamination_note": (
                "Model selection was contaminated by test-set inspection. On the "
                "validation split GradientBoosting/A_weather_only ranks first "
                "(0.618) ahead of LogisticRegression/A_weather_only (0.601); the "
                "latter was selected citing its test ROC-AUC of 0.777. Recorded "
                "here so the baseline's provenance is not misrepresented."
            ),
        }

    # ---- target + split definition as the baseline defined them ----
    inv["target_definition"] = {
        "column": "flood_next_7d",
        "rule": "1 iff a day- or month-precision DesInventar event occurs at the same "
                "location within (t, t+7]",
        "year_precision_events": "excluded from positives; implicitly treated as NEGATIVE "
                                 "days, which the corrected pipeline changes",
        "sources_used": ["DesInventar (UNDRR)"],
    }

    for name in ("train", "validation", "test"):
        p = C.BASELINE_PROCESSED_DIR / f"{name}.csv"
        if p.exists():
            d = pd.read_csv(p, usecols=["date", "location", "flood_next_7d"],
                            parse_dates=["date"], low_memory=False)
            inv["splits"][name] = {
                "rows": int(len(d)),
                "date_min": str(d.date.min().date()),
                "date_max": str(d.date.max().date()),
                "locations": int(d.location.nunique()),
                "positives": int(d.flood_next_7d.sum()),
                "positive_rate": round(float(d.flood_next_7d.mean()), 8),
            }

    out = C.BASELINE_MANIFEST_DIR / "baseline_manifest.json"
    out.write_text(json.dumps(inv, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  inputs inventoried      : {len(inv['inputs'])}")
    print(f"  artifact sets           : {len(inv['baseline_artifacts'])}")
    print(f"  report files            : {len(inv['baseline_reports'])}")
    for k, v in inv["splits"].items():
        print(f"  {k:11s} rows={v['rows']:>7} pos={v['positives']:>5} "
              f"rate={v['positive_rate']:.6%} {v['date_min']}->{v['date_max']}")


if __name__ == "__main__":
    main()
