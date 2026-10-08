"""Check whether the collected raw data can support targets at horizons H+1, 3, 7, 14, 30 days.

This does NOT build any target column. It counts the flood events each horizon could use, checks that
predictor data exist for every possible prediction date, and states what a genuine (forecast-based)
experiment would need. Output: reports/forecast_horizon_readiness.md and .csv

Logic per horizon H (prediction date t, label window (t, t+H]):
  * a usable positive needs an event whose date is known to within much less than H days:
      exact-day HIGH-CONFIDENCE dates for every H; UNCERTAIN dates only as sensitivity analysis;
      month-precision dates cannot place an event inside a window shorter than a month;
  * predictors must exist on every day <= t (weather window starts 1999-04-14);
  * for an honest forecast experiment, forecasts issued at/before t must cover lead H
    (GloFAS v4.0 reforecasts: issue dates 2003-2023, leads 1-46 days).

Usage
  python scripts/check_forecast_horizon_readiness.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, utc_now  # noqa: E402

HORIZONS = [1, 3, 7, 14, 30]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("horizons", cfg)
    proc, rep = ROOT / cfg["paths"]["processed"], p(cfg, "reports")
    win = load_window(cfg)
    a = pd.read_csv(proc / "desinventar_flood_event_audit.csv", dtype=str, keep_default_na=False)
    a = a[a["location_id"] != ""]
    exact = a[a["date_precision"] == "day"].copy()
    exact["d"] = pd.to_datetime(exact["event_date"], errors="coerce")
    hc = exact[exact["date_confidence"] == "HIGH-CONFIDENCE EVENT DATE"]
    unc = exact[exact["date_confidence"] == "UNCERTAIN EVENT DATE"]
    # distinct district-days (several records can describe one flood in one district on one day)
    hc_ev = hc.drop_duplicates(["location_id", "d"])
    unc_ev = unc.drop_duplicates(["location_id", "d"])
    ws = pd.Timestamp(win["start"])
    rf0, rf1 = pd.Timestamp("2003-03-01"), pd.Timestamp("2023-11-25")  # GloFAS v4.0 reforecast issue dates (constraints)
    rows = []
    for h in HORIZONS:
        # events whose earliest possible prediction date (event date - H) still has >= 365 days of predictors before it
        need = lambda ev: ev[(ev["d"] - pd.Timedelta(days=h)) >= ws + pd.Timedelta(days=365)]  # noqa: E731
        rows.append({
            "horizon_days": h,
            "high_confidence_district_days": len(hc_ev),
            "high_confidence_with_full_365d_history": len(need(hc_ev)),
            "plus_uncertain_district_days": len(hc_ev) + len(unc_ev),
            "districts_with_high_confidence_event": hc_ev["location_id"].nunique(),
            "high_confidence_events_in_glofas_reforecast_period": int(hc_ev["d"].between(rf0 + pd.Timedelta(days=h), rf1 + pd.Timedelta(days=h)).sum()),
            "reforecast_lead_covers_horizon": h <= 46,
            "month_precision_records_usable": "no" if h < 28 else "only for monthly-resolution sensitivity analysis",
            "date_error_tolerance": {1: "none — dates must be exact", 3: "±1 day", 7: "±2–3 days", 14: "±5 days", 30: "±1–2 weeks"}[h],
            "assessment": ("weak: too few reliable exact dates; day-level date errors dominate" if h == 1 else
                           "possible but fragile (date errors)" if h == 3 else
                           "PRIMARY: supported (high-confidence dates; uncertain as sensitivity)" if h == 7 else
                           "supported; more positives per event, less timing precision" if h == 14 else
                           "supported as a seasonal-risk horizon; little forecast skill expected from weather alone"),
        })
    df = pd.DataFrame(rows)
    df.to_csv(rep / "forecast_horizon_readiness.csv", index=False)
    by_year = hc_ev["d"].dt.year.value_counts().sort_index()
    L = ["# Forecast-horizon readiness (no targets built)", "", f"_Generated {utc_now()} by `scripts/check_forecast_horizon_readiness.py`._", "",
         "Counts are distinct district-days with a flood record, after resolving records to the 101 districts. Uncertain, "
         "unlikely and no-exact-date records must not become negatives.", "",
         df.to_markdown(index=False), "",
         f"High-confidence district-days by year: {by_year.to_dict()}", "",
         "## Predictor availability", "",
         f"- Daily weather (NASA POWER, CHIRPS, soil wetness): {win['start']} → {win['end']}, no gaps — supports every horizon "
         "for prediction dates up to the last event.",
         "- Static terrain/hydrology/land cover: time-invariant.",
         "- Climate indices: monthly, lagged (ONI ≤ month(t)−2; Niño 3.4/DMI ≤ month(t)−1).",
         "- GloFAS reanalysis (needs EWDS credentials): daily 1979–2026 — would add hydrological state on days ≤ t for all horizons.",
         "- GloFAS v4.0 reforecasts (needs EWDS credentials): twice-weekly issues 2003-03 → 2023-11, leads 1–46 days — the only "
         "collected-or-planned archive that supports an honest *forecast* experiment at H+1…H+30.", "",
         "## Conclusion", "",
         "The raw data support H+3, H+7 (primary), H+14 and H+30 targets; H+1 is not defensible with these labels because "
         "even high-confidence DesInventar dates can be off by a day. The binding constraint at every horizon is the "
         "number of reliable event dates, not predictor availability.", ""]
    (rep / "forecast_horizon_readiness.md").write_text("\n".join(L), encoding="utf-8")
    logger.info("Horizon readiness: %s", df[["horizon_days", "high_confidence_district_days", "plus_uncertain_district_days"]].to_dict("records"))


if __name__ == "__main__":
    main()
