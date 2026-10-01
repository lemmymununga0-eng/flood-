"""Phase 4, 5 - flood-label reconciliation with full provenance.

The audit established that every one of the nine independently documented flood events in
this project's own curated log is labelled 0 in the data the production model learns from,
and that ten consecutive training years (1990-1999) plus four recent years contain no
events at all. The negative class therefore means "no flood was recorded", not "no flood
occurred".

This script does NOT simply add those events as positives. It builds an auditable
provenance table over three documentary sources and assigns each candidate one of five
decisions, governed by the Phase 5 label-quality rules:

  POSITIVE_DAY      day-precision date AND a resolvable district -> real positive
  POSITIVE_MONTH    month-precision date (window <= 31 days) AND a district -> positive,
                    over the documented window, flagged as month precision
  MASK_EPISODE      the source documents that flooding occurred somewhere in a region
                    over a long window, but not which days or which district. The window
                    is EXCLUDED from both classes rather than asserted either way.
  MASK_YEAR         year-precision only. Never a positive (a year-precision event would
                    flag ~365 days), and -- the correction -- never a negative either.
                    The baseline treated these days as negatives, which is affirmatively
                    wrong: a flood is documented to have happened in that location-year.
  EXCLUDE           no defensible date, or no resolvable location. Contributes nothing.

Masking is the conservative half of the fix. It removes contaminated negatives without
inventing a single positive that the sources do not support.

Outputs (small, version-controlled, in-repo):
    ml/labels/candidate_events.csv      one row per candidate, with evidence
    ml/labels/authoritative_events.csv  the accepted positive/mask intervals
    ml/labels/label_reconciliation.json summary counts

    python ml/pipeline/p04_reconcile_labels.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402

MAX_MONTH_WINDOW_DAYS = 31   # beyond this a "month-level" range is really an episode
MAX_DAY_WINDOW_DAYS = 14     # a day-precision window longer than this is an episode


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_locations() -> list[str]:
    return sorted(pd.read_csv(C.LOCATIONS_CSV)["name"].astype(str).str.strip().unique())


def district_province_map() -> dict[str, str]:
    d = pd.read_csv(C.DESINVENTAR_CSV)
    m: dict[str, str] = {}
    for row in d.itertuples():
        dist = str(getattr(row, "district", "") or "").strip()
        prov = str(getattr(row, "province", "") or "").strip()
        if dist and prov and dist not in m:
            m[dist] = prov
    return m


def parse_desinventar_date(raw: str) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    """Reproduces the baseline's precision logic exactly, so the two pipelines
    classify DesInventar dates identically. 'YYYY/MM/DD' with '--' placeholders."""
    if not isinstance(raw, str):
        return pd.NaT, pd.NaT, "unparseable"
    m = re.match(r"^\s*(\d{4})/(\d{2}|--)/(\d{2}|--)\s*$", raw)
    if not m:
        ts = pd.to_datetime(raw, errors="coerce")
        return (ts, ts, "day") if pd.notna(ts) else (pd.NaT, pd.NaT, "unparseable")
    y, mo, da = m.groups()
    if mo == "--":
        ts = pd.Timestamp(int(y), 1, 1)
        return ts, ts + pd.offsets.YearEnd(0), "year"
    if da == "--":
        ts = pd.Timestamp(int(y), int(mo), 1)
        return ts, ts + pd.offsets.MonthEnd(0), "month"
    try:
        ts = pd.Timestamp(int(y), int(mo), int(da))
    except ValueError:
        return pd.NaT, pd.NaT, "unparseable"
    return ts, ts, "day"


def match_districts(text: str, known: list[str]) -> list[str]:
    """Exact, case-insensitive, word-boundary match of known district names inside a
    free-text location description. Deliberately conservative: no fuzzy matching, so a
    district is only credited when the source names it. Unmatched text yields nothing
    rather than a guess."""
    if not isinstance(text, str) or not text.strip():
        return []
    low = text.lower()
    hits = []
    for name in known:
        if re.search(rf"\b{re.escape(name.lower())}\b", low):
            hits.append(name)
    return hits


def classify(start: pd.Timestamp, end: pd.Timestamp, precision: str,
             districts: list[str], provinces: list[str]) -> tuple[str, str]:
    """Return (decision, reason) per the Phase 5 rules."""
    if pd.isna(start):
        return "EXCLUDE", "no parseable date"
    if precision == "year":
        return "MASK_YEAR", (
            "year-precision only: cannot be a positive (would flag ~365 days) and must "
            "not be a negative (a flood is documented in this location-year)"
        )
    span = int((end - start).days) + 1 if pd.notna(end) else 1

    if not districts:
        if provinces:
            return "MASK_EPISODE", (
                f"date is {precision}-precision but only province-level location "
                f"({', '.join(provinces)}); cannot attribute to a district, so the "
                f"window is excluded from both classes rather than asserted"
            )
        return "EXCLUDE", "no resolvable district or province"

    if precision == "month":
        if span <= MAX_MONTH_WINDOW_DAYS:
            return "POSITIVE_MONTH", f"month-precision window of {span} days over a named district"
        return "MASK_EPISODE", (
            f"month-precision range spans {span} days (> {MAX_MONTH_WINDOW_DAYS}); this is a "
            f"seasonal episode, not a dated event, so no day can be asserted positive"
        )

    # day precision
    if span <= MAX_DAY_WINDOW_DAYS:
        return "POSITIVE_DAY", f"day-precision window of {span} day(s) over a named district"
    return "POSITIVE_DAY_ONSET_ONLY", (
        f"day-precision onset recorded, but the window spans {span} days "
        f"(> {MAX_DAY_WINDOW_DAYS}); onset day is positive and the remainder is masked, "
        f"because the source does not document which later days flooded"
    )


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def from_desinventar(known: list[str]) -> list[dict]:
    d = pd.read_csv(C.DESINVENTAR_CSV)
    out = []
    for i, row in enumerate(d.itertuples()):
        dist = str(getattr(row, "district", "") or "").strip()
        prov = str(getattr(row, "province", "") or "").strip()
        start, end, prec = parse_desinventar_date(str(getattr(row, "date", "")))
        districts = [dist] if dist in known else []
        decision, reason = classify(start, end, prec, districts, [prov] if prov else [])
        out.append({
            "event_id": f"DI-{getattr(row, 'serial', i)}",
            "source": "DesInventar (UNDRR)",
            "date_start": start, "date_end": end, "date_precision": prec,
            "districts": ";".join(districts), "provinces": prov,
            "evidence": f"DesInventar national disaster inventory record, event='{getattr(row, 'event', '')}'",
            "evidence_url": "https://www.desinventar.net/DesInventar/profiletab.jsp?countrycode=zmb",
            "decision": decision, "decision_reason": reason,
        })
    return out


def from_dfo(known: list[str]) -> list[dict]:
    d = pd.read_csv(C.DFO_CSV)
    out = []
    for row in d.itertuples():
        start = pd.to_datetime(str(getattr(row, "Began", "")), format="%Y%m%d", errors="coerce")
        end = pd.to_datetime(str(getattr(row, "Ended", "")), format="%Y%m%d", errors="coerce")
        if pd.isna(end):
            end = start
        text = str(getattr(row, "Detailed_L", "") or "")
        districts = match_districts(text, known)
        decision, reason = classify(start, end, "day", districts, [])
        out.append({
            "event_id": f"DFO-{getattr(row, 'Register__', '?')}",
            "source": "Dartmouth Flood Observatory (Brakenridge, Univ. of Colorado)",
            "date_start": start, "date_end": end, "date_precision": "day",
            "districts": ";".join(districts), "provinces": "",
            "evidence": f"DFO Global Active Archive of Large Flood Events; GLIDE="
                        f"{getattr(row, 'Glide__', '')}; cause={getattr(row, 'Main_cause', '')}; "
                        f"detail='{text[:120].replace(chr(10), ' ')}'",
            "evidence_url": "https://floodobservatory.colorado.edu/Archives/index.html",
            "decision": decision, "decision_reason": reason,
        })
    return out


def from_curated(known: list[str], d2p: dict[str, str]) -> list[dict]:
    """The project's own hand-compiled, individually-sourced log. These are the events
    the audit proved are currently labelled 0."""
    d = pd.read_csv(C.CURATED_EVENTS_CSV)
    out = []
    for row in d.itertuples():
        start = pd.to_datetime(getattr(row, "start_date", None), errors="coerce")
        end = pd.to_datetime(getattr(row, "end_date", None), errors="coerce")
        if pd.isna(end):
            end = start
        dist_text = str(getattr(row, "districts", "") or "")
        prov_text = str(getattr(row, "provinces", "") or "")
        districts = match_districts(dist_text, known)
        provinces = [p.strip() for p in prov_text.split(",") if p.strip()]
        span = int((end - start).days) + 1 if pd.notna(start) and pd.notna(end) else 1
        # The log itself states which entries are month-level only.
        notes = str(getattr(row, "confidence_notes", "") or "")
        prec = "month" if re.search(r"month-level", notes, re.I) else "day"
        decision, reason = classify(start, end, prec, districts, provinces)
        out.append({
            "event_id": str(getattr(row, "event_id", "?")),
            "source": f"Curated log: {getattr(row, 'source_name', '')}",
            "date_start": start, "date_end": end, "date_precision": prec,
            "districts": ";".join(districts), "provinces": prov_text,
            "evidence": (f"span={span}d; affected={getattr(row, 'people_or_households_affected', '')}; "
                         f"notes={notes[:160]}"),
            "evidence_url": str(getattr(row, "source_url", "") or ""),
            "decision": decision, "decision_reason": reason,
        })
    return out


# ---------------------------------------------------------------------------

def main() -> None:
    C.ensure_out_dirs()
    known = load_locations()
    d2p = district_province_map()
    prov_to_districts: dict[str, list[str]] = {}
    for dist, prov in d2p.items():
        if dist in known:
            prov_to_districts.setdefault(prov, []).append(dist)

    rows = from_desinventar(known) + from_dfo(known) + from_curated(known, d2p)
    cand = pd.DataFrame(rows)

    # ---- what the baseline label says about each candidate, for the before/after ----
    cand["baseline_label"] = cand["date_precision"].map(
        {"day": "positive", "month": "positive", "year": "NEGATIVE (contaminated)",
         "unparseable": "negative (excluded)"}
    ).fillna("negative")
    cand.loc[cand.decision.eq("EXCLUDE"), "baseline_label"] = "negative (excluded)"
    cand["proposed_label"] = cand["decision"].map({
        "POSITIVE_DAY": "positive", "POSITIVE_MONTH": "positive",
        "POSITIVE_DAY_ONSET_ONLY": "positive (onset) + masked remainder",
        "MASK_EPISODE": "masked (neither class)", "MASK_YEAR": "masked (neither class)",
        "EXCLUDE": "excluded (contributes nothing)",
    })

    cand = cand.sort_values(["date_start", "event_id"])
    cand_out = C.LABELS_DIR / "candidate_events.csv"
    cand.to_csv(cand_out, index=False)

    # ---- authoritative intervals: one row per (location, interval, kind) ----
    auth = []
    for r in cand.itertuples():
        if pd.isna(r.date_start):
            continue
        dl = [d for d in str(r.districts).split(";") if d]
        if r.decision in ("POSITIVE_DAY", "POSITIVE_MONTH"):
            for loc in dl:
                auth.append({"location": loc, "start": r.date_start, "end": r.date_end,
                             "kind": "POSITIVE", "precision": r.date_precision,
                             "event_id": r.event_id, "source": r.source})
        elif r.decision == "POSITIVE_DAY_ONSET_ONLY":
            for loc in dl:
                auth.append({"location": loc, "start": r.date_start, "end": r.date_start,
                             "kind": "POSITIVE", "precision": "day",
                             "event_id": r.event_id, "source": r.source})
                auth.append({"location": loc,
                             "start": r.date_start + pd.Timedelta(days=1), "end": r.date_end,
                             "kind": "MASK", "precision": "episode",
                             "event_id": r.event_id, "source": r.source})
        elif r.decision == "MASK_YEAR":
            for loc in dl or []:
                auth.append({"location": loc, "start": r.date_start, "end": r.date_end,
                             "kind": "MASK", "precision": "year",
                             "event_id": r.event_id, "source": r.source})
        elif r.decision == "MASK_EPISODE":
            targets = dl or [d for p in str(r.provinces).split(",")
                             for d in prov_to_districts.get(p.strip(), [])]
            for loc in dict.fromkeys(targets):
                auth.append({"location": loc, "start": r.date_start, "end": r.date_end,
                             "kind": "MASK", "precision": "episode",
                             "event_id": r.event_id, "source": r.source})

    auth_df = pd.DataFrame(auth).drop_duplicates()
    auth_out = C.LABELS_DIR / "authoritative_events.csv"
    auth_df.to_csv(auth_out, index=False)

    # ---- summary ----
    summary = {
        "generated": "2026-09-26",
        "sources": {
            "DesInventar (UNDRR)": int((cand.source.str.startswith("DesInventar")).sum()),
            "Dartmouth Flood Observatory": int((cand.source.str.startswith("Dartmouth")).sum()),
            "Curated log (DMMU/WARMA/ReliefWeb/FloodList/Charter)":
                int((cand.source.str.startswith("Curated")).sum()),
        },
        "decisions": {k: int(v) for k, v in cand.decision.value_counts().items()},
        "date_precision": {k: int(v) for k, v in cand.date_precision.value_counts().items()},
        "authoritative_intervals": {
            "POSITIVE": int((auth_df.kind == "POSITIVE").sum()) if len(auth_df) else 0,
            "MASK": int((auth_df.kind == "MASK").sum()) if len(auth_df) else 0,
            "distinct_locations": int(auth_df.location.nunique()) if len(auth_df) else 0,
        },
        "rules": {
            "MAX_MONTH_WINDOW_DAYS": MAX_MONTH_WINDOW_DAYS,
            "MAX_DAY_WINDOW_DAYS": MAX_DAY_WINDOW_DAYS,
            "year_precision": "masked, never positive and never negative",
            "district_matching": "exact case-insensitive word-boundary match; no fuzzy matching",
        },
    }
    (C.LABELS_DIR / "label_reconciliation.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print(f"candidates       : {len(cand)}  -> {cand_out.name}")
    for k, v in cand.decision.value_counts().items():
        print(f"    {k:26s} {v}")
    print(f"auth intervals   : {len(auth_df)}  -> {auth_out.name}")
    print(f"    POSITIVE {summary['authoritative_intervals']['POSITIVE']}   "
          f"MASK {summary['authoritative_intervals']['MASK']}   "
          f"locations {summary['authoritative_intervals']['distinct_locations']}")


if __name__ == "__main__":
    main()
