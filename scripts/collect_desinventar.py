"""Collect the DesInventar Zambia database: download the official export, preserve it, extract it.

Outputs
  data/raw/desinventar/original/DI_export_zmb.zip (+ .provenance.json)   untouched original
  data/raw/desinventar/extracted/                                         unzipped files, verbatim
  data/raw/desinventar/extracted/tables/*.csv                             every XML table as CSV, values verbatim
  data/processed/desinventar_flood_events.csv     FLOOD + FLASH FLOODS records, raw fields + parsed date columns
  data/processed/collection_window.json           weather date window derived from valid flood dates
  reports/desinventar_event_type_inventory.csv    every event type, counts, flood-related review flags
  reports/desinventar_flood_keyword_hits.csv      non-flood records whose text mentions flooding (for review)

Usage
  python scripts/collect_desinventar.py            # reuse the cached ZIP if present
  python scripts/collect_desinventar.py --force    # download again (new ZIP is kept alongside, never overwritten)
"""
from __future__ import annotations

import argparse
import calendar
import html
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ROOT, get_logger, get_with_retry, load_config, make_session, p,  # noqa: E402
                     record_failure, sha256_file, utc_now, write_json)

TABLES = ["eventos", "causas", "niveles", "regiones", "extensiontabs", "diccionario",
          "fichas", "extension", "level_maps", "level_attributes"]


def download(cfg, logger, force: bool) -> Path:
    d = cfg["desinventar"]
    out_dir = p(cfg, "raw_desinventar_original")
    target = out_dir / d["export_zip_filename"]
    if target.exists() and not force:
        logger.info("Cached original found, not downloading again: %s", target.relative_to(ROOT))
        return target
    if target.exists() and force:
        # never overwrite an original: keep the new one under a dated name
        target = out_dir / f"{target.stem}_{date.today():%Y%m%d}{target.suffix}"
    session = make_session(cfg)
    url = d["export_zip_url"]
    logger.info("Downloading %s", url)
    try:
        r = get_with_retry(session, url, cfg, logger, stream=True)
    except Exception as e:  # noqa: BLE001
        record_failure(cfg, "desinventar", "export_zip", url, repr(e), getattr(e, "attempts", 1))
        raise SystemExit(f"DesInventar download failed: {e}")
    tmp = target.with_suffix(".part")
    with open(tmp, "wb") as fh:
        for chunk in r.iter_content(1 << 16):
            fh.write(chunk)
    tmp.replace(target)
    if not zipfile.is_zipfile(target):
        raise SystemExit(f"Downloaded file is not a ZIP archive: {target}")
    write_json(target.with_suffix(".provenance.json"), {
        "source": d["name"], "url": url, "retrieved_utc": utc_now(),
        "http_status": r.status_code, "content_type": r.headers.get("Content-Type"),
        "last_modified": r.headers.get("Last-Modified"), "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
    })
    logger.info("Saved %s (%d bytes)", target.relative_to(ROOT), target.stat().st_size)
    return target


def extract(zip_path: Path, cfg, logger) -> Path:
    out = p(cfg, "raw_desinventar_extracted")
    with zipfile.ZipFile(zip_path) as z:
        members = z.infolist()
        for m in members:
            dest = out / m.filename
            if dest.exists() and dest.stat().st_size == m.file_size:
                continue
            z.extract(m, out)
        logger.info("Extracted %d members to %s", len(members), out.relative_to(ROOT))
    xmls = list(out.glob("*.xml"))
    if len(xmls) != 1:
        raise SystemExit(f"Expected one XML export in {out}, found {xmls}")
    return xmls[0]


def parse_tables(xml_path: Path) -> dict[str, pd.DataFrame]:
    """Every <section><TR>..</TR></section> table in the export, all values kept as strings."""
    root = ET.parse(xml_path).getroot()
    tables = {}
    for section in root:
        rows = [{c.tag: (c.text or "") for c in tr} for tr in section.findall("TR")]
        tables[section.tag] = pd.DataFrame(rows, dtype="string")
    return tables


def parse_date(year: str, month: str, day: str, max_year: int, min_year: int) -> dict:
    """Interpret DesInventar fechano/fechames/fechadia without inventing anything.

    Returns the most precise date the record supports and a precision/quality label.
    """
    out = {"event_start_date": pd.NA, "date_precision": "invalid", "date_quality_flag": ""}
    try:
        y = int(year)
    except (TypeError, ValueError):
        out["date_quality_flag"] = "year_not_numeric"
        return out
    if not (min_year <= y <= max_year) or len(str(year).strip()) != 4:
        out["date_quality_flag"] = f"implausible_year:{year}"
        return out
    m = int(month) if str(month).strip().isdigit() else 0
    dd = int(day) if str(day).strip().isdigit() else 0
    if m == 0:
        out.update(date_precision="year", event_start_date=f"{y:04d}")
        if dd:
            out["date_quality_flag"] = "day_without_month"
        return out
    if not 1 <= m <= 12:
        out["date_quality_flag"] = f"invalid_month:{month}"
        return out
    if dd == 0:
        out.update(date_precision="month", event_start_date=f"{y:04d}-{m:02d}")
        return out
    if dd > calendar.monthrange(y, m)[1]:
        out["date_quality_flag"] = f"invalid_day:{y}-{m}-{dd}"
        return out
    out.update(date_precision="day", event_start_date=f"{y:04d}-{m:02d}-{dd:02d}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--force", action="store_true", help="download the export again")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("desinventar", cfg)
    d = cfg["desinventar"]

    zip_path = download(cfg, logger, args.force)
    xml_path = extract(zip_path, cfg, logger)
    tables = parse_tables(xml_path)
    tdir = p(cfg, "raw_desinventar_extracted") / "tables"
    tdir.mkdir(exist_ok=True)
    for name, df in tables.items():
        df.to_csv(tdir / f"{name}.csv", index=False, encoding="utf-8")
    logger.info("Wrote %d XML tables to %s", len(tables), tdir.relative_to(ROOT))

    fichas, ext = tables["fichas"], tables["extension"]
    logger.info("DesInventar records (fichas): %d, extension rows: %d", len(fichas), len(ext))
    # Join the extension (disaggregated loss) fields on the record key. Raw columns are untouched.
    ext_cols = [c for c in ext.columns if c != "clave_ext" and c not in fichas.columns]
    records = fichas.merge(ext[["clave_ext", *ext_cols]], how="left", left_on="clave", right_on="clave_ext")
    records.to_csv(tdir.parent / "desinventar_all_records_joined.csv", index=False, encoding="utf-8")

    # ---- event-type inventory (flood + review categories) -------------------------------------
    flood_types, review_types = d["flood_event_types"], d["review_event_types"]
    kw = re.compile("|".join(re.escape(k) for k in d["flood_keywords"]), re.I)
    text = (records["lugar"].fillna("") + " " + records["descausa"].fillna("") + " " +
            records["di_comments"].fillna("") + " " + records["causa"].fillna("") + " " +
            records["otros"].fillna(""))
    explicit = re.compile("flood|inundat|submerg|overflow", re.I)  # explicit flooding words, not just rain
    records_kw = records.assign(_kw=text.str.contains(kw), _kw_explicit=text.str.contains(explicit),
                                matched_keywords=text.str.findall(kw).map(
                                    lambda m: ";".join(sorted({x.lower() for x in m}))))
    declared = set(tables["eventos"]["nombre"])
    inv = []
    for ev in sorted(declared | set(records["evento"])):
        sub = records_kw[records_kw["evento"] == ev]
        role = ("included_flood" if ev in flood_types else
                "review_possibly_flood_related" if ev in review_types else "excluded_not_flood")
        inv.append({"event_type": ev, "records": len(sub), "role": role,
                    "records_with_flood_keywords": int(sub["_kw"].sum()),
                    "records_with_explicit_flood_words": int(sub["_kw_explicit"].sum()),
                    "declared_in_eventos_table": ev in declared})
    inv = pd.DataFrame(inv).sort_values("records", ascending=False)
    reports = p(cfg, "reports")
    inv.to_csv(reports / "desinventar_event_type_inventory.csv", index=False)
    hits = records_kw[records_kw["_kw"] & ~records_kw["evento"].isin(flood_types)]
    hits[["serial", "evento", "matched_keywords", "fechano", "fechames", "fechadia", "name0", "name1", "lugar",
          "causa", "descausa", "di_comments"]].to_csv(reports / "desinventar_flood_keyword_hits.csv", index=False)
    for t in flood_types:
        if t not in declared:
            logger.warning("Configured flood type %r is not declared in this database", t)
    logger.info("Flood-type records: %s", {t: int((records["evento"] == t).sum()) for t in flood_types})
    logger.info("Non-flood records mentioning flood keywords (for review, NOT included): %d", len(hits))

    # ---- flood event table with parsed dates (raw fields preserved alongside) -------------------
    floods = records[records["evento"].isin(flood_types)].copy()
    retrieved = date.today()
    parsed = pd.DataFrame([parse_date(r.fechano, r.fechames, r.fechadia, retrieved.year, d["valid_year_min"])
                           for r in floods.itertuples()], index=floods.index)
    floods = pd.concat([floods, parsed], axis=1)
    # A day-precision date in the future relative to retrieval is impossible: flag, do not drop.
    future = (floods["date_precision"] == "day") & (pd.to_datetime(floods["event_start_date"], errors="coerce")
                                                     > pd.Timestamp(retrieved))
    floods.loc[future, "date_quality_flag"] = "date_after_retrieval"
    # Duration (DesInventar 'duracion', days) gives an end date only when the source states it (> 0).
    dur = pd.to_numeric(floods["duracion"], errors="coerce")
    start_dt = pd.to_datetime(floods["event_start_date"].where(floods["date_precision"] == "day"), errors="coerce")
    floods["event_end_date_from_duration"] = (start_dt + pd.to_timedelta(dur.where(dur > 0) - 1, unit="D")
                                              ).dt.strftime("%Y-%m-%d")
    floods["province_original"] = floods["name0"]
    floods["district_original"] = floods["name1"]
    floods["location_original"] = floods["lugar"]
    floods["retrieved_utc"] = utc_now()
    floods["source"] = "DesInventar Zambia (UNDRR) — " + zip_path.name
    out = p(cfg, "processed") / "desinventar_flood_events.csv"
    floods.to_csv(out, index=False, encoding="utf-8")
    logger.info("Flood events written: %d -> %s", len(floods), out.relative_to(ROOT))
    logger.info("Date precision: %s", floods["date_precision"].value_counts().to_dict())

    # ---- collection window ----------------------------------------------------------------------
    usable = floods[floods["date_precision"].isin(["day", "month"]) & (floods["date_quality_flag"] == "")]
    starts = pd.to_datetime(usable["event_start_date"], format="mixed")
    ends = starts.where(usable["date_precision"] == "day", starts + pd.offsets.MonthEnd(0))
    w = cfg["collection_window"]
    window = {
        "earliest_flood_date": starts.min().date().isoformat(),
        "latest_flood_date": ends.max().date().isoformat(),
        "lookback_days": w["lookback_days"], "horizon_days": w["horizon_days"],
        "start": (starts.min() - timedelta(days=w["lookback_days"])).date().isoformat(),
        "end": (ends.max() + timedelta(days=w["horizon_days"])).date().isoformat(),
        "basis": "valid day- and month-precision FLOOD/FLASH FLOODS start dates "
                 "(month precision counted as the whole month); year-only and invalid dates excluded",
        "n_records_used": int(len(usable)), "derived_utc": utc_now(),
    }
    write_json(p(cfg, "processed") / "collection_window.json", window)
    logger.info("Collection window: %s -> %s (floods %s -> %s)", window["start"], window["end"],
                window["earliest_flood_date"], window["latest_flood_date"])


if __name__ == "__main__":
    main()
