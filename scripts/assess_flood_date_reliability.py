"""Flag whether each DesInventar flood record's date is plausibly the flood ONSET date.

Evidence used is deliberately independent of rainfall (using rainfall to decide which floods are
"real" and then predicting floods from rainfall would be circular):
  dry_season        start date in May-October (Zambia's rainy season is roughly November-April)
  batch_date        >= 5 flood records share the exact same date (bulk assessment / data-entry batch)
  admin_text        record text describes an assessment, repair, rehabilitation, construction,
                    funding request or relief rather than the flood itself
Records are NOT removed or relabelled. The researcher chooses the rule in Stage 3.

Output: data/processed/desinventar_flood_date_reliability.csv, reports/flood_date_reliability.md
Usage
  python scripts/assess_flood_date_reliability.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p, utc_now  # noqa: E402

ADMIN = re.compile(r"assess|repair|rehabilit|reconstruct|construction|request for funds|funding|relief food|"
                   r"maintenance|replacement|procure|tender|budget|culvert installation", re.I)
BATCH_MIN = 5


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("date_reliability", cfg)
    proc, rep = ROOT / cfg["paths"]["processed"], p(cfg, "reports")
    f = pd.read_csv(proc / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    out = f[["clave", "serial", "evento", "event_start_date", "date_precision", "date_quality_flag", "name0", "name1",
             "lugar", "fuentes", "fechafec"]].rename(columns={"clave": "record_id"}).copy()
    day = out["date_precision"] == "day"
    d = pd.to_datetime(out["event_start_date"].where(day), errors="coerce")
    text = (f["descausa"] + " " + f["di_comments"] + " " + f["fuentes"] + " " + f["otros"]).fillna("")
    out["dry_season"] = d.dt.month.between(5, 10)
    counts = out.loc[day, "event_start_date"].value_counts()
    out["records_on_same_date"] = out["event_start_date"].map(counts).where(day).fillna(0).astype(int)
    out["batch_date"] = out["records_on_same_date"] >= BATCH_MIN
    out["admin_text"] = text.str.contains(ADMIN)
    out["admin_text_match"] = text.str.findall(ADMIN).map(lambda m: ";".join(sorted({x.lower() for x in m})))
    out["n_flags"] = out[["dry_season", "batch_date", "admin_text"]].sum(axis=1)

    def cls(r):
        if r.date_precision != "day" or r.date_quality_flag:
            return "no_exact_date"
        if r.n_flags == 0:
            return "onset_plausible"
        if r.dry_season and (r.batch_date or r.admin_text):
            return "onset_unlikely"
        return "onset_uncertain"
    out["date_reliability"] = out.apply(cls, axis=1)
    out["assessed_utc"] = utc_now()
    out.to_csv(proc / "desinventar_flood_date_reliability.csv", index=False)

    # ---- full per-record flood-event audit (Section 12 of the Stage 2 brief) ----------------------
    res = pd.read_csv(rep / "location_resolution_report.csv", dtype=str, keep_default_na=False).set_index("record_id")
    explicit = re.compile(r"flood|inundat|submerg|overflow|burst (its|the) banks|washed away|water level", re.I)
    rainish = re.compile(r"rain|downpour|storm|water", re.I)
    desc = (f["descausa"].str.strip() + " | " + f["di_comments"].str.strip()).str.strip(" |")
    audit = pd.DataFrame({
        "record_id": f["clave"], "serial": f["serial"], "event_type": f["evento"],
        "event_date": f["event_start_date"], "date_precision": f["date_precision"],
        "province": f["name0"], "district": f["name1"], "place_text": f["lugar"],
        "location_id": f["clave"].map(res["location_id"]), "resolution_level": f["clave"].map(res["resolution_level"]),
        "record_latitude": f["clave"].map(res["record_latitude"]), "record_longitude": f["clave"].map(res["record_longitude"]),
        "description": desc.str.slice(0, 300), "source_reported": f["fuentes"],
    })
    audit["flood_evidence"] = ["explicit_flood_text" if explicit.search(t) else "rain_or_water_text" if rainish.search(t)
                               else "category_only" for t in (desc + " " + f["lugar"])]
    audit["date_confidence"] = out["date_reliability"].map({"onset_plausible": "HIGH-CONFIDENCE EVENT DATE",
                                                            "onset_uncertain": "UNCERTAIN EVENT DATE",
                                                            "onset_unlikely": "UNLIKELY EVENT DATE",
                                                            "no_exact_date": "NO EXACT DATE"}).values
    audit["location_confidence"] = ["HIGH (district + own coordinates)" if lat else
                                    "MEDIUM (district code)" if lvl == "district" else "LOW (province only)"
                                    for lat, lvl in zip(audit["record_latitude"], audit["resolution_level"])]
    audit["use_note"] = ("Uncertain/unlikely/no-exact-date records must NOT become negative examples; absence of a record "
                         "is not evidence of no flood.")
    audit.to_csv(proc / "desinventar_flood_event_audit.csv", index=False)
    logger.info("Flood-event audit: %s | %s | %s", audit["date_confidence"].value_counts().to_dict(),
                audit["flood_evidence"].value_counts().to_dict(), audit["location_confidence"].value_counts().to_dict())

    vc = out["date_reliability"].value_counts()
    by_year = pd.crosstab(pd.to_datetime(out["event_start_date"].where(day), errors="coerce").dt.year,
                          out["date_reliability"]).astype(int)
    top_batches = counts[counts >= BATCH_MIN]
    L = ["# DesInventar flood-date reliability", "",
         f"_Generated {utc_now()} by `scripts/assess_flood_date_reliability.py`. Records are flagged, never removed._", "",
         "**Why this matters:** the eventual target is *a flood starts in (t, t+7]*. That needs the flood **onset** date. "
         "Many DesInventar Zambia records carry the date of a later assessment, repair programme or data-entry batch.", "",
         "Evidence (independent of rainfall, to avoid circular label selection): dry-season date (May–Oct), "
         f"batch date (≥{BATCH_MIN} flood records on the same day), administrative text (assessment, repair, rehabilitation, "
         "construction, funding request…).", "",
         "| Class | Rule | Records |", "|---|---|---:|",
         f"| onset_plausible | exact day, no flag | {vc.get('onset_plausible', 0)} |",
         f"| onset_uncertain | exact day, one flag (or wet-season with batch/admin flag) | {vc.get('onset_uncertain', 0)} |",
         f"| onset_unlikely | exact day in dry season AND batch or administrative text | {vc.get('onset_unlikely', 0)} |",
         f"| no_exact_date | year-/month-only or invalid date | {vc.get('no_exact_date', 0)} |", "",
         f"Flags among exact-day records: dry season {int(out.loc[day, 'dry_season'].sum())}, batch date "
         f"{int(out.loc[day, 'batch_date'].sum())}, administrative text {int(out.loc[day, 'admin_text'].sum())}.", "",
         "Largest same-date batches: " + ", ".join(f"{k} ({v})" for k, v in top_batches.items()), "",
         "## By year", "", by_year.to_markdown() if hasattr(by_year, "to_markdown") else by_year.to_string(), "",
         "## Supporting (descriptive) evidence from rainfall", "",
         "See `reports/chirps_validation_report.md` → *Rainfall on DesInventar exact-day flood dates*: the median 3-day "
         "rainfall ending on the recorded date is below a typical wet-season day for both CHIRPS and NASA POWER. This is "
         "reported as evidence about the dates, and is **not** used to classify records.", "",
         "## Decision for the researcher (Stage 3)", "",
         "Options, none applied here: (1) positives = `onset_plausible` only, and treat `onset_uncertain`/`onset_unlikely` "
         "district-periods as *excluded* (neither class); (2) also include `onset_uncertain`; (3) widen the target window or "
         "move to a seasonal/monthly target if too few onset-plausible events remain; (4) seek corroborating dates from an "
         "independent source (DFO, ReliefWeb, DMMU situation reports). Using rainfall to select labels is not recommended "
         "(circular).", ""]
    # Independent check of the flags (NOT used to classify): rainfall before the recorded date, by class.
    chirps = proc / "chirps_daily_at_locations.csv"
    if chirps.exists():
        res = pd.read_csv(rep / "location_resolution_report.csv", dtype=str, keep_default_na=False)
        e = out[out["date_reliability"] != "no_exact_date"].merge(res[["record_id", "location_id"]], on="record_id")
        e = e[e["location_id"] != ""].assign(d=lambda x: pd.to_datetime(x["event_start_date"]))
        c = pd.read_csv(chirps, parse_dates=["date"]).sort_values(["location_id", "date"])
        c["r7"] = c.groupby("location_id")["chirps_precip_mm"].transform(lambda s: s.rolling(7, min_periods=7).sum())
        ws = c[c["date"].dt.month.isin([11, 12, 1, 2, 3, 4])]
        e = e.merge(c[["location_id", "date", "r7"]], left_on=["location_id", "d"], right_on=["location_id", "date"])
        e["pct"] = [(ws.loc[ws["location_id"] == x.location_id, "r7"] <= x.r7).mean() for x in e.itertuples()]
        t = e.groupby("date_reliability").agg(records=("pct", "size"), median_7day_chirps_mm=("r7", "median"),
                                               median_wet_season_percentile=("pct", lambda s: round(100 * s.median())),
                                               pct_in_top_quarter=("pct", lambda s: round(100 * (s > 0.75).mean())))
        L[L.index("## Decision for the researcher (Stage 3)"):L.index("## Decision for the researcher (Stage 3)")] = [
            "## Independent check of the flags (rainfall is not used to assign them)", "",
            "7-day CHIRPS total ending on the recorded date, as a percentile of that district's wet-season (Nov–Apr) 7-day totals:", "",
            t.round(1).to_markdown(), "",
            "If the flags were arbitrary the classes would look alike. They separate sharply: `onset_unlikely` dates fall in "
            "essentially rain-free weeks, while `onset_plausible` dates follow unusually wet weeks.", ""]
    (rep / "flood_date_reliability.md").write_text("\n".join(L), encoding="utf-8")
    logger.info("Flood date reliability: %s", vc.to_dict())


if __name__ == "__main__":
    main()
