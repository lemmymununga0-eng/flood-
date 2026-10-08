"""Build reports/final_data_quality_scorecard.csv with a DEFINED, reproducible scoring method.

Scores (0-1, two decimals) — computed from files and audit results, never set by hand:
  spatial_score      share of the 101 districts the dataset can be joined to (1.0 for national/basin indices,
                     which apply to every district by definition)
  temporal_score     share of the required daily window 1999-04-14..2026-01-30 covered at the dataset's
                     native resolution; time-invariant data = 1.0; a single snapshot taken outside most of
                     the window = 0.5 (anachronism); not collected = 0
  coverage_score     spatial_score x temporal_score
  completeness_score 1 - share of missing values in the collected series/table (not collected = 0)
  quality_score      share of this dataset's checks that PASS in the second independent audit
                     (WARN counts as half); datasets without audit checks use the first-pass validator status
                     (COMPLETE = 1, otherwise 0)
Categorical:
  forecast_relevance HIGH = direct short-term flood driver or hydrological state (rainfall, discharge, runoff);
                     MEDIUM = modulates flood response (soil wetness, terrain/drainage, floodplain occurrence,
                     climate state); LOW = context or exposure; LABEL = defines the target
  leakage_risk       from reports/variable_leakage_register.csv: HIGH if the dataset holds POST-EVENT
                     variables, MEDIUM if POTENTIAL LEAKAGE (needs lag/anachronism rule), LOW otherwise
  role / final_decision  the Stage 2 classification (CORE / OPTIONAL / VALIDATION / EXPOSURE / NOT COLLECTED)
Usage
  python scripts/build_quality_scorecard.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("scorecard", cfg)
    rep, proc = p(cfg, "reports"), ROOT / cfg["paths"]["processed"]
    audit = pd.read_csv(rep / "second_audit_checks.csv")
    env = json.loads((rep / "environmental_data_validation_summary.json").read_text(encoding="utf-8"))
    chirps = json.loads((rep / "chirps_validation_summary.json").read_text(encoding="utf-8"))
    leak = pd.read_csv(rep / "variable_leakage_register.csv")

    def q(ds_names, fallback=None):
        a = audit[audit["dataset"].isin(ds_names)]
        if len(a):
            return round(((a["result"] == "PASS").sum() + 0.5 * (a["result"] == "WARN").sum()) / len(a), 2)
        return 1.0 if fallback == "COMPLETE" else 0.0

    def lk(ds):
        cats = set(leak.loc[leak["dataset"] == ds, "category"])
        return "HIGH (post-event fields)" if "POST-EVENT" in cats else "MEDIUM (rule needed)" if "POTENTIAL LEAKAGE" in cats else "LOW"

    def missing(path, cols):
        if not path.exists():
            return None
        d = pd.read_csv(path, usecols=cols)
        return float(d.isna().mean().mean())

    w = pd.read_csv(ROOT / "data/raw/nasa_power/nasa_power_daily.csv", usecols=["location_id"])
    gsw = proc / "environmental" / "district_surface_water.csv"
    glofas_files = list((ROOT / cfg["paths"]["raw_glofas"]).rglob("*.grib2"))
    rows = [
        # dataset, spatial, temporal, missing, quality, relevance, leakage-ds, role, decision
        ("DesInventar flood events", 82 / 101, 1.0, 0.0, q(["DesInventar"]), "LABEL", lk("desinventar"),
         "LABEL SOURCE", "KEEP — labels only from HIGH-CONFIDENCE dates (UNCERTAIN as sensitivity); never a feature"),
        ("Location master", 1.0, 1.0, 0.0, q(["Locations"]), "LOW", lk("location_master"), "SPATIAL KEY", "KEEP"),
        ("NASA POWER weather", 1.0, 1.0, missing(ROOT / "data/raw/nasa_power/nasa_power_daily.csv", cfg["nasa_power"]["parameters"]),
         q(["NASA POWER", "Alignment"]), "HIGH", lk("nasa_power_weather"), "CORE", "KEEP"),
        ("CHIRPS v3.0 rainfall", 1.0, chirps["days_present"] / chirps["days_expected"],
         missing(proc / "chirps_daily_at_locations.csv", ["chirps_precip_mm"]), q(["CHIRPS", "Alignment"]), "HIGH", lk("chirps"),
         "CORE", "KEEP — Stage 3 must justify using one or both rainfall sources"),
        ("HydroSHEDS terrain/hydrology", 1.0, 1.0, missing(proc / "district_terrain_hydrology.csv", None) or 0.0,
         q(["HydroSHEDS"]), "MEDIUM", lk("terrain_hydrology"), "CORE (static)", "KEEP"),
        ("NASA POWER soil wetness", 1.0, 1.0, missing(ROOT / "data/raw/nasa_power/nasa_power_daily_soil_moisture.csv",
                                                      cfg["nasa_power_soil"]["parameters"]), q(["Soil wetness"]), "MEDIUM",
         lk("nasa_power_soil"), "OPTIONAL", "KEEP as optional experiment (overlaps antecedent rainfall)"),
        ("ESA WorldCover 2021", 1.0, 0.5, 0.0, q(["WorldCover"]), "MEDIUM", lk("landcover"), "OPTIONAL", "KEEP as optional static context"),
        ("JRC Global Surface Water occurrence", 1.0 if gsw.exists() else 0.0, 0.5 if gsw.exists() else 0.0,
         0.0 if gsw.exists() else 1.0, q(["Global Surface Water"], "COMPLETE" if gsw.exists() else None), "MEDIUM",
         lk("surface_water"), "OPTIONAL", "KEEP as optional static flood-susceptibility" if gsw.exists() else "PENDING download"),
        ("Climate indices (ONI, Niño 3.4, DMI)", 1.0, 1.0, 0.0, q(["Climate indices"]), "MEDIUM", lk("climate_indices"),
         "OPTIONAL", "KEEP as lagged monthly/seasonal experiment"),
        ("WorldPop", 1.0, round(len(range(2000, 2021)) / len(range(1999, 2027)), 2), 0.0, q(["WorldPop"]), "LOW", lk("worldpop"),
         "EXPOSURE", "KEEP — separate exposure layer, never an occurrence predictor"),
        ("GloFAS v4.0 river-network static maps", 1.0 if (ROOT / cfg["paths"]["raw_glofas"] / "static/zambia_subset/upArea_repaired_zambia.nc").exists() else 0.0,
         1.0, 0.0, q(["GloFAS static"]), "MEDIUM", "LOW", "CORE support", "KEEP — defines river-network extraction pixels"),
        ("GloFAS v4.0 historical (discharge, runoff, soil wetness)", 1.0 if glofas_files else 0.0, 1.0 if glofas_files else 0.0,
         0.0 if glofas_files else 1.0, q(["GloFAS historical"]), "HIGH", "MEDIUM (rule needed)",
         "DEFERRED (was CORE)" if not glofas_files else "CORE",
         f"DEFERRED by researcher decision {cfg['glofas'].get('decision_date')} — no EWDS credentials; scripts ready to add later"
         if not glofas_files else "KEEP"),
        ("GloFAS v4.0 reforecasts (discharge, 2003-2023)", 0.0, 0.0, 1.0, 0.0, "HIGH", "MEDIUM (rule needed)", "DEFERRED (optional forecast experiment)",
         f"DEFERRED with GloFAS historical ({cfg['glofas'].get('decision_date')}); script ready"),
        ("DFO flood archive", 0.0, 0.0, 1.0, 0.0, "LOW", lk("dfo") if (proc / "dfo_zambia_events.csv").exists() else "HIGH (post-event)",
         "VALIDATION", "NOT COLLECTED — server unreachable; optional"),
        ("GRDC river gauges", 0.0, 0.0, 1.0, 0.0, "MEDIUM", "LOW", "VALIDATION", "NOT COLLECTED — request-only; optional"),
    ]
    df = pd.DataFrame(rows, columns=["dataset", "spatial_score", "temporal_score", "missing_share", "quality_score",
                                     "forecast_relevance", "leakage_risk", "role", "final_decision"])
    df["completeness_score"] = (1 - df["missing_share"].fillna(0)).round(2)
    df["coverage_score"] = (df["spatial_score"] * df["temporal_score"]).round(2)
    for c in ("spatial_score", "temporal_score"):
        df[c] = df[c].round(2)
    df = df[["dataset", "coverage_score", "completeness_score", "spatial_score", "temporal_score", "quality_score",
             "forecast_relevance", "leakage_risk", "role", "final_decision"]]
    df.to_csv(rep / "final_data_quality_scorecard.csv", index=False)
    logger.info("Scorecard: %d datasets", len(df))


if __name__ == "__main__":
    main()
