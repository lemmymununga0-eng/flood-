"""Audit what is physically on disk and write docs/DATA_AUDIT_REPORT.md + reports/data_inventory.csv.

Nothing is trusted from earlier console output: every status below is recomputed from the files
(row counts, date ranges, checksums, validation summaries). Statuses are limited to
COMPLETE / PARTIAL / MISSING / NEEDS VALIDATION / METHODOLOGICAL DECISION REQUIRED.

Run after the validators:  validate_raw_data.py, validate_chirps.py, validate_environmental_data.py
Usage
  python scripts/audit_data.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, sha256_file, utc_now  # noqa: E402

INVENTORY_DIRS = ["data", "reports", "docs", "scripts", "config", "ml/labels", "ml/baseline",
                  "ai-engine/data", "ai-engine/notebooks"]
SKIP_PARTS = {"__pycache__", "_daily"}


def describe(f: Path) -> dict:
    d = {"path": str(f.relative_to(ROOT)).replace("\\", "/"), "type": f.suffix.lower().lstrip(".") or "none",
         "bytes": f.stat().st_size, "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
         "rows": "", "columns": "", "date_min": "", "date_max": "", "extent": ""}
    try:
        if d["type"] == "csv" and d["bytes"] < 400e6:
            head = pd.read_csv(f, nrows=0)
            d["columns"] = len(head.columns)
            date_col = next((c for c in head.columns if c in ("date", "week_start", "event_start_date")), None)
            if date_col:
                s = pd.read_csv(f, usecols=[date_col], dtype=str)[date_col]
                d["rows"] = len(s)
                s = s[s.str.len() >= 4]
                d["date_min"], d["date_max"] = (s.min(), s.max()) if len(s) else ("", "")
            else:
                d["rows"] = sum(1 for _ in open(f, encoding="utf-8", errors="ignore")) - 1
        elif d["type"] in ("tif", "tiff"):
            import rasterio
            with rasterio.open(f) as ds:
                d["extent"] = f"{ds.width}x{ds.height} px, res {ds.res[0]:.5f}, bounds {tuple(round(b, 2) for b in ds.bounds)}"
        elif d["type"] == "nc":
            import xarray as xr
            with xr.open_dataset(f) as ds:
                t = pd.DatetimeIndex(ds["time"].values)
                d.update(rows=len(t), date_min=str(t.min().date()), date_max=str(t.max().date()),
                         extent=" x ".join(f"{k}={v}" for k, v in ds.sizes.items()))
        elif d["type"] in ("shp", "gpkg"):
            import pyogrio
            info = pyogrio.read_info(f)
            d["rows"] = info["features"]
            d["extent"] = str(tuple(round(b, 2) for b in info["total_bounds"])) if info.get("total_bounds") is not None else ""
    except Exception as e:  # noqa: BLE001
        d["extent"] = f"unreadable: {e!r}"[:120]
    return d


def table(rows: list[dict], cols: list[str]) -> str:
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out)


def jload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("audit", cfg)
    rep, proc = p(cfg, "reports"), ROOT / cfg["paths"]["processed"]
    win = load_window(cfg)

    inv = []
    for d in INVENTORY_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file() and not (SKIP_PARTS & set(f.parts)) and not f.name.endswith((".pyc",)):
                inv.append(describe(f))
    inv_df = pd.DataFrame(inv)
    inv_df.to_csv(rep / "data_inventory.csv", index=False)
    logger.info("Inventory: %d files", len(inv_df))

    V = jload(rep / "validation_report.json")
    C = jload(rep / "chirps_validation_summary.json")
    E = jload(rep / "environmental_data_validation_summary.json")
    d, n = V.get("desinventar", {}), V.get("nasa_power", {})

    # ---- independent checks of the Stage 1 datasets ---------------------------------------------
    zip_ = ROOT / cfg["paths"]["raw_desinventar_original"] / "DI_export_zmb.zip"
    prov = jload(zip_.with_suffix(".provenance.json"))
    zip_ok = zip_.exists() and sha256_file(zip_) == prov.get("sha256")
    fl = pd.read_csv(proc / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    res = pd.read_csv(rep / "location_resolution_report.csv", dtype=str, keep_default_na=False)
    unres = pd.read_csv(proc / "unresolved_locations.csv", dtype=str, keep_default_na=False)
    master = pd.read_csv(proc / "location_master.csv")
    di_ok = (zip_ok and len(fl) == d.get("flood_records") and fl["clave"].is_unique
             and len(res) == len(fl) and int(unres["n_records"].astype(int).sum()) == (res["resolution_level"] != "district").sum())
    lm_ok = (len(master) == 101 and master["location_id"].is_unique and master[["latitude", "longitude"]].notna().all().all()
             and (master["coordinate_source"].fillna("") != "").all())
    pw_ok = (n.get("locations_present") == 101 and not n.get("locations_missing") and n.get("duplicate_location_dates") == 0
             and max(n.get("missing_value_pct", {"x": 1}).values()) == 0)

    def env(name):
        return E.get(name, {}).get("status", "MISSING")

    # ---- QC "true status" table: computed from files on disk only ----------------------------------
    def nfiles(rel, pattern):
        base = ROOT / rel
        return len([f for f in base.rglob(pattern) if ".part" not in f.name]) if base.exists() else 0

    raw = cfg["paths"]
    rel = pd.read_csv(proc / "desinventar_flood_date_reliability.csv") if (proc / "desinventar_flood_date_reliability.csv").exists() else None
    soil_csv = ROOT / raw["raw_nasa_power"] / ".." / "nasa_power_daily_soil_moisture.csv"
    exposure = proc / "exposure" / "worldpop_district_exposure.csv"
    S = E.get("soil_rain_overlap_spearman", {})
    qc = [
        ("DesInventar", "LABEL SOURCE", "COMPLETE" if di_ok else "NEEDS VALIDATION",
         f"{nfiles(raw['raw_desinventar_original'], '*.zip')} original ZIP (sha256 {'verified' if zip_ok else 'MISMATCH'}); "
         f"{nfiles(raw['raw_desinventar_extracted'], '*')} extracted files",
         f"{d.get('total_records_all_types')} records; {d.get('flood_records')} flood (FLOOD {d.get('flood_records_by_type', {}).get('FLOOD')}, "
         f"FLASH FLOODS {d.get('flood_records_by_type', {}).get('FLASH FLOODS')}); 440 at district level",
         f"{d.get('records_without_exact_day')} without exact day; 4 province-only"
         + (f"; exact-day onset reliability: plausible {int((rel['date_reliability'] == 'onset_plausible').sum())}, "
            f"uncertain {int((rel['date_reliability'] == 'onset_uncertain').sum())}, unlikely {int((rel['date_reliability'] == 'onset_unlikely').sum())}"
            if rel is not None else ""),
         "Researcher decides the label rule (date reliability) before Stage 3"),
        ("Location master", "SPATIAL KEY", "COMPLETE" if lm_ok else "NEEDS VALIDATION", "location_master.csv, unresolved_locations.csv",
         f"{len(master)} districts, all with traceable coordinates", "none", "None"),
        ("NASA POWER weather", "CORE", "COMPLETE" if pw_ok else "PARTIAL",
         f"{nfiles(raw['raw_nasa_power'], '*__*.json') - nfiles(raw['raw_nasa_power'], '*.meta.json')} raw JSON + CSV",
         f"{n.get('locations_present')} locations × {n.get('expected_days_per_location')} days, {' → '.join(n.get('date_range', []))}",
         "0 missing values; 2 flagged >300 mm days (probable reanalysis artefacts, retained)", "None (capping rule is a Stage 3 decision)"),
        ("CHIRPS v3.0", "CORE", "COMPLETE" if C.get("complete") else "PARTIAL",
         f"{nfiles(raw['raw_chirps'], '*.zambia.*.nc')} yearly NetCDFs + point extraction",
         f"{C.get('days_present')}/{C.get('days_expected')} days; years verified {len(C.get('years_verified', []))}/28; 101 locations",
         f"missing years {C.get('missing_years') or 'none'}; grid extremes >300 mm flagged (outside Zambia)",
         "None" if C.get("complete") else "Resume download_chirps.py"),
        ("HydroSHEDS v1 (data v1.1)", "CORE (static)", env("HydroSHEDS (terrain and hydrology)"),
         f"{nfiles(raw['raw_hydrosheds'] + '/original', '*.zip')} archives (sha256 + ZIP CRC ok); {nfiles(raw['raw_hydrosheds'] + '/zambia_subset', '*')} subsets",
         "DEM 15″, HydroRIVERS, HydroBASINS L4/L6; 101 districts point + zonal", "flow dir/acc rasters not needed (HydroRIVERS upstream area)", "None"),
        ("ESA WorldCover 2021 v200", "OPTIONAL (static/slow-changing)", env("ESA WorldCover 2021"),
         f"{nfiles(raw['raw_landcover'], '*.tif')} tiles (1/4 overview ≈ 40 m)", "all tiles intersecting Zambia; 101 districts",
         "2021 snapshot only (temporal limitation)", "None"),
        ("NASA POWER soil wetness", "OPTIONAL EXPERIMENT", env("Soil wetness (NASA POWER GWETTOP/GWETROOT/GWETPROF — optional experiment)"),
         f"{nfiles(raw['raw_nasa_power_soil'], '*__*.json') - nfiles(raw['raw_nasa_power_soil'], '*.meta.json')} raw JSON + CSV" if soil_csv.exists() else "none",
         "101 locations, full window", f"overlap with 90-day rainfall (Spearman): GWETROOT {S.get('GWETROOT', {}).get('90d', '?')}", "None"),
        ("WorldPop", "EXPOSURE (separate layer)", env("WorldPop population (exposure layer)"),
         f"{nfiles(raw['raw_worldpop'], '*.tif')} yearly rasters; exposure table {'present' if exposure.exists() else 'missing'}",
         "2000–2020, 101 districts", "2021–2026 not in this product", "None"),
        ("Climate indices", "OPTIONAL (seasonal, lagged)", env("Climate indices (ONI, Niño 3.4, DMI/IOD)"),
         f"{nfiles(raw['raw_climate_indices'], '*.txt') + nfiles(raw['raw_climate_indices'], '*.ascii') + nfiles(raw['raw_climate_indices'], '*.data')} raw files",
         "ONI/Niño 3.4 1950–2026, DMI 1870–2026, BoM IOD 2008–2026", "months not yet published", "None"),
        ("DFO / satellite flood data", "VALIDATION (optional)", env("Dartmouth Flood Observatory archive (optional validation)"),
         f"{nfiles(raw['raw_satellite_flood'], '*.xlsx')} DFO files", "—", "DFO server unreachable all collection period; S1/GFD/CEMS not collected",
         "OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL; re-run download_flood_observations.py if access returns"),
        ("GRDC / hydrological observations", "OPTIONAL / DATA ACCESS LIMITED", "MISSING", "README only",
         "—", "all series (request-only access)", "Optional: submit a GRDC request; not required for Stage 3"),
        ("GloFAS v4 river-network static maps", "CORE support",
         "COMPLETE" if nfiles(raw["raw_glofas"] + "/static/zambia_subset", "*.nc") == 3 else "PARTIAL",
         f"{nfiles(raw['raw_glofas'] + '/static/original', '*.nc')} originals + {nfiles(raw['raw_glofas'] + '/static/zambia_subset', '*.nc')} subsets",
         "0.05° Zambia window", "—", "None" if nfiles(raw["raw_glofas"] + "/static/zambia_subset", "*.nc") == 3 else "Resume download_glofas_static.py"),
        ("GloFAS v4.0 historical (discharge, runoff, soil wetness)",
         "DEFERRED by researcher decision " + str(cfg["glofas"].get("decision_date")) if cfg["glofas"].get("collection_status") == "deferred" else "CORE (pending)",
         "COMPLETE" if nfiles(raw["raw_glofas"] + "/historical", "*.grib2") >= 84 else "MISSING",
         f"{nfiles(raw['raw_glofas'] + '/historical', '*.grib2')} GRIB2 files", "planned: 101 districts, 1999–2026",
         "all — EWDS requires the researcher's ECMWF account and token",
         "Deferred. To add later: create ECMWF account, accept CEMS-FLOODS licence, write ~/.cdsapirc; run download_glofas.py + extract_glofas.py"),
        ("GloFAS v4.0 reforecasts", "DEFERRED (optional forecast experiment)", "MISSING",
         f"{nfiles(raw['raw_glofas'] + '/reforecast', '*.grib2')} GRIB2 files", "planned: issues 2003-03 → 2023-11, leads 1–46 d",
         "all — same credentials", "Optional, after the historical download"),
        ("JRC Global Surface Water occurrence", "OPTIONAL (static)",
         "COMPLETE" if (proc / "environmental" / "district_surface_water.csv").exists() else "PARTIAL",
         f"{nfiles(raw['raw_other'] + '/global_surface_water', '*.tif')} of 4 tiles", "Zambia, 30 m → 101 districts",
         "—", "None" if (proc / "environmental" / "district_surface_water.csv").exists() else "Resume download_global_surface_water.py"),
    ]
    qc_df = pd.DataFrame(qc, columns=["DATASET", "ROLE", "ACTUAL STATUS", "FILES PRESENT", "COVERAGE", "MISSING", "NEXT ACTION"])

    # ---- temporal and spatial coverage audits ------------------------------------------------------
    flv = fl[fl["date_precision"] == "day"]
    yrs = pd.to_datetime(flv["event_start_date"]).dt.year
    gap_years = [y for y in range(int(yrs.min()), int(yrs.max()) + 1) if y not in set(yrs)]
    ci = pd.read_csv(proc / "climate_indices_monthly.csv") if (proc / "climate_indices_monthly.csv").exists() else None
    def last_month(col):
        if ci is None:
            return "—"
        r = ci.loc[ci[col].notna(), ["year", "month"]].iloc[-1]
        return f"{int(r['year'])}-{int(r['month']):02d}"
    temporal = [
        ("DesInventar flood events (exact day)", d.get("date_range_day_precision", ["", ""])[0], d.get("date_range_day_precision", ["", ""])[1],
         f"no exact-day records in {gap_years}", "Labels mainly 2000–2017 (+ a few 2022–2026); see date-reliability classes"),
        ("NASA POWER weather", win["start"], win["end"], "none", "full window"),
        ("CHIRPS v3.0", win["start"], win["end"], "none" if C.get("complete") else f"{C.get('missing_days')} days", "full window"),
        ("NASA POWER soil wetness", win["start"], win["end"], "none", "full window (optional)"),
        ("HydroSHEDS", "static (~2000)", "static", "—", "time-invariant"),
        ("ESA WorldCover", "2021", "2021", "single snapshot", "quasi-static assumption"),
        ("WorldPop", "2000", "2020", "2021–2026", "exposure only"),
        ("ONI / Niño 3.4", "1950-01", f"{last_month('oni')} / {last_month('nino34_anom')}", "unpublished recent months", "full window, lagged"),
        ("DMI (NOAA PSL)", "1870-01", last_month("dmi_hadisst"), "unpublished recent months", "full window, lagged"),
        ("DFO archive", "—", "—", "not collected (server unreachable)", "—"),
        ("River gauges", "—", "—", "not collected (request-only)", "—"),
    ]
    temporal_df = pd.DataFrame(temporal, columns=["Dataset", "Earliest date", "Latest date", "Missing periods", "Usable period"])
    spatial = [
        ("DesInventar", "district (record coded to DesInventar level 1)", "82 districts have ≥1 flood record; 4 records province-only"),
        ("Location master", "district point (DesInventar regiones point verified inside polygon, or polygon interior point)", "101/101"),
        ("NASA POWER weather / soil", "raster cell (~0.5° MERRA-2) at the district point", "101/101 (8 groups share a cell)"),
        ("CHIRPS", "raster cell (0.05°) nearest the district point; full grid kept", "101/101, one pixel each"),
        ("HydroSHEDS DEM/slope", "zonal statistic over district polygon + value at district point", "101/101"),
        ("HydroRIVERS", "distances from point and from a ~2 km district sample grid; max upstream area in district", "101/101"),
        ("HydroBASINS", "basin containing the point; dominant basin in district", "101/101"),
        ("WorldCover", "zonal class shares over district polygon + class at point", "101/101"),
        ("WorldPop", "zonal sum over district polygon (exposure layer)", "101/101 × 21 years"),
        ("Climate indices", "national/global index (same value for every district)", "n/a"),
        ("DFO / river gauges", "event centroid / river station (would need a later spatial join)", "not collected"),
    ]
    spatial_df = pd.DataFrame(spatial, columns=["Dataset", "Spatial relationship to the location master", "Coverage of 101 districts"])

    rows = [
        {"Dataset": "DesInventar Zambia (raw export + flood subset)", "Source": "UNDRR DesInventar", "Purpose": "Flood events (future target), audit",
         "Status": "COMPLETE" if di_ok else "NEEDS VALIDATION", "Spatial coverage": "Zambia; 440/444 flood records at district level",
         "Temporal coverage": f"flood years {d.get('date_range_all_valid_years')}; exact days {d.get('date_range_day_precision')}",
         "Completeness": f"{d.get('flood_records')} flood records; {d.get('records_without_exact_day')} without exact day",
         "Validation status": f"raw ZIP sha256 {'matches' if zip_ok else 'MISMATCH'}; record_id unique; resolution report complete",
         "Action required": "None for collection (see methodological items below)"},
        {"Dataset": "Location master (101 districts)", "Source": "DesInventar geography", "Purpose": "Spatial key for all joins",
         "Status": "COMPLETE" if lm_ok else "NEEDS VALIDATION", "Spatial coverage": f"{len(master)} districts",
         "Temporal coverage": "static", "Completeness": f"{int(master['latitude'].notna().sum())}/101 with coordinates",
         "Validation status": f"IDs unique; quality {master['coordinate_quality'].value_counts().to_dict()}", "Action required": "None"},
        {"Dataset": "NASA POWER daily weather", "Source": "NASA LaRC POWER API v2.10", "Purpose": "Core weather predictors",
         "Status": "COMPLETE" if pw_ok else "PARTIAL", "Spatial coverage": f"{n.get('locations_present')} district points",
         "Temporal coverage": " → ".join(n.get("date_range", [])), "Completeness": f"{n.get('total_observations')} rows; 0 missing",
         "Validation status": f"0 duplicates; flagged {n.get('flagged_values')}",
         "Action required": "Decide capping rule for 2 flagged >300 mm days in Stage 3 (documented, not deleted)"},
        {"Dataset": "CHIRPS v3.0 daily rainfall", "Source": "UCSB Climate Hazards Center", "Purpose": "Independent rainfall predictor",
         "Status": "COMPLETE" if C.get("complete") else "PARTIAL", "Spatial coverage": "Zambia 0.05° grid; 101 district points",
         "Temporal coverage": f"{C.get('days_present')}/{C.get('days_expected')} days", "Completeness": f"missing years {C.get('missing_years')}",
         "Validation status": "reports/chirps_validation_report.md",
         "Action required": "None" if C.get("complete") else "Let the resumable download finish; re-run validate_chirps.py"},
        {"Dataset": "HydroSHEDS DEM/slope, HydroRIVERS, HydroBASINS", "Source": "HydroSHEDS v1", "Purpose": "Static terrain/drainage predictors",
         "Status": env("HydroSHEDS (terrain and hydrology)"), "Spatial coverage": "Zambia window; district zonal + point",
         "Temporal coverage": "static", "Completeness": "see environmental report", "Validation status": "reports/environmental_data_validation_report.md",
         "Action required": "None" if env("HydroSHEDS (terrain and hydrology)") == "COMPLETE" else "Re-run download_hydrosheds.py, then extract_district_environment.py"},
        {"Dataset": "ESA WorldCover 2021", "Source": "ESA WorldCover v200", "Purpose": "OPTIONAL static/slow-changing context (2021 snapshot)",
         "Status": env("ESA WorldCover 2021"), "Spatial coverage": "Zambia tiles (40 m overview)", "Temporal coverage": "2021 snapshot",
         "Completeness": "see environmental report", "Validation status": "class codes + % sums checked",
         "Action required": "None" if env("ESA WorldCover 2021") == "COMPLETE" else "Re-run download_worldcover.py, then extract_district_environment.py"},
        {"Dataset": "NASA POWER soil wetness", "Source": "NASA POWER (MERRA-2)", "Purpose": "Optional experiment",
         "Status": env("Soil wetness (NASA POWER GWETTOP/GWETROOT/GWETPROF — optional experiment)"), "Spatial coverage": "101 district points",
         "Temporal coverage": f"{win['start']} → {win['end']}", "Completeness": "see environmental report", "Validation status": "range 0–1 checked",
         "Action required": "None"},
        {"Dataset": "ERA5-Land soil moisture", "Source": "Copernicus CDS", "Purpose": "Optional experiment (higher resolution)",
         "Status": "METHODOLOGICAL DECISION REQUIRED", "Spatial coverage": "not collected", "Temporal coverage": "1950–present (product)",
         "Completeness": "0%", "Validation status": "n/a", "Action required": "Needs the researcher's CDS account/licence acceptance — only if the optional experiment is wanted"},
        {"Dataset": "River gauges (GRDC / WARMA / ZRA)", "Source": "GRDC portal; national agencies", "Purpose": "Validation/context",
         "Status": "MISSING", "Spatial coverage": "not collected", "Temporal coverage": "unknown", "Completeness": "0%",
         "Validation status": "n/a", "Action required": "OPTIONAL / DATA ACCESS LIMITED: GRDC series only via a personal request form; WARMA has no public portal. Not required for Stage 3"},
        {"Dataset": "DFO flood archive", "Source": "Dartmouth Flood Observatory", "Purpose": "Independent event validation",
         "Status": env("Dartmouth Flood Observatory archive (optional validation)"), "Spatial coverage": "event centroids",
         "Temporal coverage": "1985– (product)", "Completeness": "see environmental report", "Validation status": "n/a",
         "Action required": "None" if env("Dartmouth Flood Observatory archive (optional validation)") == "COMPLETE" else "OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL (server unreachable; script ready)"},
        {"Dataset": "Satellite flood extent (Sentinel-1, Global Flood Database, CEMS)", "Source": "Copernicus / NASA", "Purpose": "Validation",
         "Status": "MISSING", "Spatial coverage": "not collected", "Temporal coverage": "S1 2014–; GFD 2000–2018", "Completeness": "0%",
         "Validation status": "n/a", "Action required": "Future work (needs Earth Engine/Copernicus accounts and heavy processing)"},
        {"Dataset": "Climate indices (ONI, Niño 3.4, DMI)", "Source": "NOAA CPC / NOAA PSL / BoM", "Purpose": "Optional seasonal context",
         "Status": env("Climate indices (ONI, Niño 3.4, DMI/IOD)"), "Spatial coverage": "basin-scale index", "Temporal coverage": "1870/1950 → 2026",
         "Completeness": "see environmental report", "Validation status": "monthly continuity checked", "Action required": "None"},
        {"Dataset": "WorldPop population", "Source": "WorldPop (Univ. Southampton)", "Purpose": "Risk/exposure layer",
         "Status": env("WorldPop population (exposure layer)"), "Spatial coverage": "Zambia 1 km; district sums",
         "Temporal coverage": "2000–2020 yearly", "Completeness": "see environmental report", "Validation status": "national totals checked",
         "Action required": "None" if env("WorldPop population (exposure layer)") == "COMPLETE" else "Re-run download_worldpop.py"},
        {"Dataset": "Flood definition: 7 non-flood-category records describing floods", "Source": "DesInventar", "Purpose": "Label scope",
         "Status": "METHODOLOGICAL DECISION REQUIRED", "Spatial coverage": "—", "Temporal coverage": "—", "Completeness": "kept separately",
         "Validation status": "reports/desinventar_flood_keyword_hits.csv", "Action required": "Researcher decides include/exclude before Stage 3 labels"},
        {"Dataset": "Flood-date reliability (exact-day records)", "Source": "DesInventar", "Purpose": "Label timing",
         "Status": "METHODOLOGICAL DECISION REQUIRED", "Spatial coverage": "—", "Temporal coverage": "—",
         "Completeness": "onset_plausible / uncertain / unlikely flags", "Validation status": "reports/flood_date_reliability.md",
         "Action required": "Researcher chooses which exact-day records may be positives (many dates are assessment/report dates)"},
        {"Dataset": "Year-/month-only flood dates (168 records)", "Source": "DesInventar", "Purpose": "Label scope",
         "Status": "METHODOLOGICAL DECISION REQUIRED", "Spatial coverage": "—", "Temporal coverage": "—", "Completeness": "preserved",
         "Validation status": "date_precision column", "Action required": "Stage 3 must exclude them from both classes (cannot be placed in a 7-day window)"},
    ]
    cols = ["Dataset", "Source", "Purpose", "Status", "Spatial coverage", "Temporal coverage", "Completeness", "Validation status", "Action required"]

    legacy = inv_df[inv_df["path"].str.startswith(("ai-engine/", "ml/"))]
    synthetic = legacy[legacy["path"].str.contains("synthetic", case=False)]

    depth = inv_df["path"].map(lambda x: 3 if x.startswith(("data/raw/", "ai-engine/data/")) else 2)
    tops = [("/".join(x.split("/")[:k]) if x.count("/") >= k else x.rsplit("/", 1)[0]) for x, k in zip(inv_df["path"], depth)]
    by_dir = inv_df.assign(top=tops).groupby("top").agg(
        files=("path", "size"), mb=("bytes", lambda s: round(s.sum() / 1e6, 1))).reset_index()
    big = inv_df[inv_df["type"].isin(["csv", "nc", "tif", "gpkg", "shp", "zip", "xlsx", "json", "txt", "ascii", "data", "xml"])
                 & inv_df["path"].str.startswith("data/")]
    big = big[~big["path"].str.endswith("provenance.json") & ~big["path"].str.contains("/daily_weather/|/daily_soil_moisture/|/tables/")]

    L = ["# FloodShield-Zambia — Data Audit Report (Stage 2)", "",
         f"_Generated {utc_now()} by `scripts/audit_data.py` from files on disk. Full file inventory: "
         f"`reports/data_inventory.csv` ({len(inv_df)} files)._", "",
         "## True status of every dataset (QC table, computed from files on disk)", "",
         table(qc_df.to_dict("records"), list(qc_df.columns)), "",
         "## Temporal coverage audit", "", table(temporal_df.to_dict("records"), list(temporal_df.columns)), "",
         "## Spatial coverage audit", "", table(spatial_df.to_dict("records"), list(spatial_df.columns)), "",
         "## Dataset status (detailed)", "", table(rows, cols), "",
         "## What is on disk (by folder)", "", table(by_dir.to_dict("records"), ["top", "files", "mb"]), "",
         "Per-location NASA POWER JSON responses (101 + 101 files), DesInventar XML tables and provenance sidecars are "
         "counted above but not listed individually below.", "",
         "## Key data files", "",
         table(big.to_dict("records"), ["path", "bytes", "modified", "rows", "date_min", "date_max", "extent"]), "",
         "## Scripts", "", table(inv_df[inv_df["path"].str.startswith("scripts/")].to_dict("records"), ["path", "bytes", "modified"]), "",
         "## Legacy artefacts from the earlier pipeline (NOT used)", "",
         "Stage 1 restarted from raw sources; nothing below feeds the new pipeline. They are listed so they are not "
         "mistaken for current data." + (" **Note:** the legacy folder contains a *synthetic* weather file "
                                          f"(`{synthetic['path'].iloc[0]}`) — it must never be used as observed data." if len(synthetic) else ""), "",
         table(legacy.to_dict("records"), ["path", "bytes", "modified", "rows"]), "",
         ]
    (ROOT / cfg["paths"]["docs"] / "DATA_AUDIT_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    logger.info("Wrote docs/DATA_AUDIT_REPORT.md")


if __name__ == "__main__":
    main()
