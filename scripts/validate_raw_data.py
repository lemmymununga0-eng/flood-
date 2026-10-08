"""Validate the Stage 1 raw data. Flags problems; never deletes or alters any value.

Outputs (reports/)
  validation_report.json            every metric, machine-readable (input to generate_data_report.py)
  validation_report.md              human-readable summary
  missing_data_report.csv           expected vs present per dataset/location/variable
  desinventar_record_flags.csv      flood records with date/duplicate/numeric/location flags
  nasa_power_flagged_values.csv     out-of-bounds, extreme or inconsistent NASA POWER values
  chirps_flagged_values.csv         out-of-bounds or extreme CHIRPS pixel-days
  raw_checksums.csv                 sha256 of every raw file, compared with the value recorded at download

Usage
  python scripts/validate_raw_data.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, sha256_file, utc_now, write_json  # noqa: E402

DI_NUMERIC = ["muertos", "heridos", "desaparece", "afectados", "vivdest", "vivafec", "damnificados",
              "evacuados", "reubicados", "valorloc", "valorus", "nhectareas", "cabezas", "kmvias",
              "nhospitales", "nescuelas", "duracion"]
# Columns that identify a record administratively rather than describing the event.
DI_ADMIN = ["serial", "clave", "uu_id", "clave_ext", "fechafec", "fechapor", "approved", "defaultab",
            "retrieved_utc", "source"]


def vc(s: pd.Series) -> dict:
    return {str(k): int(v) for k, v in s.value_counts(dropna=False).items()}


def validate_desinventar(cfg, logger) -> tuple[dict, list[dict]]:
    proc = ROOT / cfg["paths"]["processed"]
    ext = ROOT / cfg["paths"]["raw_desinventar_extracted"]
    allrec = pd.read_csv(ext / "desinventar_all_records_joined.csv", dtype=str, keep_default_na=False)
    fl = pd.read_csv(proc / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    res = pd.read_csv(ROOT / cfg["paths"]["reports"] / "location_resolution_report.csv", dtype=str, keep_default_na=False)
    # 'serial' is re-used in this database; 'clave' is the unique record key (record_id).
    flags = pd.DataFrame({"record_id": fl["clave"], "serial": fl["serial"], "evento": fl["evento"]})

    # dates
    flags["date_precision"] = fl["date_precision"]
    flags["date_flag"] = fl["date_quality_flag"]
    entry = pd.to_datetime(fl["fechafec"], errors="coerce")
    start = pd.to_datetime(fl["event_start_date"].where(fl["date_precision"] == "day"), errors="coerce")
    entered_before = entry.notna() & start.notna() & (entry < start)
    flags.loc[entered_before, "date_flag"] = (flags.loc[entered_before, "date_flag"] + ";entered_before_event").str.strip(";")
    day = fl[fl["date_precision"] == "day"]
    valid = pd.to_datetime(day.loc[day["date_quality_flag"] == "", "event_start_date"])

    # duplicates
    content_cols = [c for c in fl.columns if c not in DI_ADMIN]
    exact = fl.duplicated(content_cols, keep=False)
    key = (fl["evento"] + "|" + fl["level1"] + "|" + fl["event_start_date"] + "|" +
           fl["lugar"].str.lower().str.replace(r"\W+", " ", regex=True).str.strip())
    probable = key.duplicated(keep=False) & ~exact
    same_day_district = (fl["level1"] + "|" + fl["event_start_date"]).where(fl["date_precision"] == "day")
    sdd = same_day_district.notna() & same_day_district.duplicated(keep=False)
    flags["exact_duplicate_group"] = np.where(exact, fl.groupby(content_cols).ngroup().astype(str), "")
    flags["probable_duplicate"] = probable
    flags["same_district_same_day"] = sdd

    # numeric consequence fields (raw; never used as predictors)
    dicc = pd.read_csv(ext / "tables" / "diccionario.csv", dtype=str, keep_default_na=False)
    ext_numeric = [c.lower() for c in dicc["nombre_campo"] if c.lower() in fl.columns]
    bad = {}
    flags["numeric_flag"] = ""
    for c in DI_NUMERIC + ext_numeric:
        v = fl[c].str.strip()
        num = pd.to_numeric(v, errors="coerce")
        nonnum = (v != "") & num.isna()
        neg = num < 0
        if nonnum.any() or neg.any():
            bad[c] = {"non_numeric": int(nonnum.sum()), "negative": int(neg.sum())}
            flags.loc[nonnum, "numeric_flag"] += f"{c}:non_numeric;"
            flags.loc[neg, "numeric_flag"] += f"{c}:negative;"

    # locations
    lr = res.set_index("record_id")
    flags["resolution_level"] = flags["record_id"].map(lr["resolution_level"])
    lat = pd.to_numeric(fl["latitude"], errors="coerce")
    lon = pd.to_numeric(fl["longitude"], errors="coerce")
    has_xy = lat.notna() & lon.notna() & ~((lat == 0) & (lon == 0))
    flags.to_csv(ROOT / cfg["paths"]["reports"] / "desinventar_record_flags.csv", index=False)

    m = {
        "total_records_all_types": int(len(allrec)),
        "event_type_counts_all": vc(allrec["evento"]),
        "flood_records": int(len(fl)),
        "flood_records_by_type": vc(fl["evento"]),
        "date_precision": vc(fl["date_precision"]),
        "date_range_day_precision": [valid.min().date().isoformat(), valid.max().date().isoformat()] if len(valid) else None,
        "date_range_all_valid_years": [fl.loc[fl["date_precision"] != "invalid", "fechano"].min(),
                                       fl.loc[fl["date_precision"] != "invalid", "fechano"].max()],
        "records_without_exact_day": int((fl["date_precision"] != "day").sum()),
        "records_by_year": vc(fl["fechano"]),
        "records_by_month_day_precision": vc(valid.dt.month),
        "suspicious_dates": vc(flags.loc[flags["date_flag"] != "", "date_flag"]),
        "suspicious_date_records": flags.loc[flags["date_flag"] != "", ["record_id", "serial", "date_flag"]].to_dict("records"),
        "duplicate_serial_numbers": int(fl["serial"].duplicated(keep=False).sum()),
        "duplicate_record_ids": int(fl["clave"].duplicated().sum()),
        "exact_duplicate_records": int(exact.sum()),
        "exact_duplicate_groups": int(flags.loc[exact, "exact_duplicate_group"].nunique()),
        "probable_duplicate_records": int(probable.sum()),
        "same_district_same_day_records": int(sdd.sum()),
        "missing_district": int((fl["level1"] == "").sum()),
        "missing_province": int((fl["level0"] == "").sum()),
        "missing_place_text": int((fl["lugar"].str.strip() == "").sum()),
        "records_with_coordinates": int(has_xy.sum()),
        "records_missing_coordinates": int((~has_xy).sum()),
        "province_distribution": vc(fl["name0"].replace("", "(none)")),
        "district_distribution": vc(fl["name1"].replace("", "(none)")),
        "provinces_represented": int(fl.loc[fl["name0"] != "", "name0"].nunique()),
        "districts_represented": int(fl.loc[fl["name1"] != "", "name1"].nunique()),
        "invalid_numeric_fields": bad,
        "location_resolution": vc(res["resolution_level"]),
    }
    logger.info("DesInventar: %d flood records, precision %s, %d exact dup, %d probable dup",
                m["flood_records"], m["date_precision"], m["exact_duplicate_records"], m["probable_duplicate_records"])
    missing_rows = [{"dataset": "desinventar", "location_id": "ALL", "variable": "event_exact_day",
                     "expected": len(fl), "present": int((fl["date_precision"] == "day").sum())},
                    {"dataset": "desinventar", "location_id": "ALL", "variable": "district",
                     "expected": len(fl), "present": int((fl["level1"] != "").sum())},
                    {"dataset": "desinventar", "location_id": "ALL", "variable": "record_coordinates",
                     "expected": len(fl), "present": int(has_xy.sum())}]
    return m, missing_rows


def validate_power(cfg, logger, window) -> tuple[dict, list[dict]]:
    n = cfg["nasa_power"]
    path = ROOT / cfg["paths"]["raw_nasa_power"] / ".." / "nasa_power_daily.csv"
    if not path.exists():
        return {"status": "missing"}, []
    df = pd.read_csv(path, parse_dates=["date"])
    master = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv")
    expected_locs = set(master.loc[master["in_weather_collection"], "location_id"])
    start = pd.Timestamp(window["start"])
    end = min(pd.Timestamp(window["end"]), pd.Timestamp.today().normalize() - pd.Timedelta(days=1))
    full = pd.date_range(start, end, freq="D")
    bounds = cfg["validation"]["bounds"]
    rows, flagged = [], []
    per_loc = {}
    for loc, g in df.groupby("location_id"):
        dates = g["date"]
        dup = int(dates.duplicated().sum())
        missing_dates = full.difference(pd.DatetimeIndex(dates))
        steps = dates.sort_values().diff().dropna().dt.days
        per_loc[loc] = {"first": dates.min().date().isoformat(), "last": dates.max().date().isoformat(),
                        "rows": int(len(g)), "missing_dates": int(len(missing_dates)), "duplicate_dates": dup,
                        "non_daily_steps": int((steps != 1).sum())}
        for v in n["parameters"]:
            rows.append({"dataset": "nasa_power", "location_id": loc, "variable": v, "expected": len(full),
                         "present": int(g[v].notna().sum())})
    for v in n["parameters"]:
        b = bounds[v]
        out = df[(df[v] < b["min"]) | (df[v] > b["max"])]
        for r in out.itertuples():
            flagged.append({"location_id": r.location_id, "date": r.date.date(), "variable": v,
                            "value": getattr(r, v), "flag": f"outside_bounds[{b['min']},{b['max']}]"})
    ext = df[df["PRECTOTCORR"] > cfg["validation"]["extreme_rain_mm"]]
    for r in ext.itertuples():
        flagged.append({"location_id": r.location_id, "date": r.date.date(), "variable": "PRECTOTCORR",
                        "value": r.PRECTOTCORR, "flag": "extreme_rain_check"})
    inc = df[df["T2M_MIN"] > df["T2M_MAX"]]
    for r in inc.itertuples():
        flagged.append({"location_id": r.location_id, "date": r.date.date(), "variable": "T2M_MIN>T2M_MAX",
                        "value": f"{r.T2M_MIN}>{r.T2M_MAX}", "flag": "inconsistent"})
    inc2 = df[(df["T2M"] < df["T2M_MIN"] - 0.05) | (df["T2M"] > df["T2M_MAX"] + 0.05)]
    for r in inc2.itertuples():
        flagged.append({"location_id": r.location_id, "date": r.date.date(), "variable": "T2M",
                        "value": r.T2M, "flag": "T2M_outside_[T2M_MIN,T2M_MAX]"})
    pd.DataFrame(flagged, columns=["location_id", "date", "variable", "value", "flag"]).to_csv(
        ROOT / cfg["paths"]["reports"] / "nasa_power_flagged_values.csv", index=False)

    # Neighbouring districts can fall in the same NASA POWER grid cell -> identical series.
    sig = df.groupby("location_id")[n["parameters"]].apply(lambda g: hash(tuple(g.round(3).fillna(-1).values.ravel())))
    shared = sig[sig.duplicated(keep=False)]
    groups = shared.groupby(shared).groups
    fails = ROOT / cfg["paths"]["reports"] / "failed_requests.csv"
    fdf = pd.read_csv(fails) if fails.exists() else pd.DataFrame(columns=["source"])
    m = {
        "locations_expected": len(expected_locs), "locations_present": int(df["location_id"].nunique()),
        "locations_missing": sorted(expected_locs - set(df["location_id"])),
        "date_range": [df["date"].min().date().isoformat(), df["date"].max().date().isoformat()],
        "expected_days_per_location": len(full), "total_observations": int(len(df)),
        "missing_value_pct": {v: round(float(100 * df[v].isna().mean()), 4) for v in n["parameters"]},
        "missing_value_count": {v: int(df[v].isna().sum()) for v in n["parameters"]},
        "locations_incomplete_coverage": {k: v for k, v in per_loc.items()
                                          if v["missing_dates"] or v["duplicate_dates"] or v["non_daily_steps"]},
        "duplicate_location_dates": int(df.duplicated(["location_id", "date"]).sum()),
        "flagged_values": vc(pd.Series([f["flag"].split("[")[0] + ":" + f["variable"] for f in flagged]))
        if flagged else {},
        "summary_stats": {v: {k: round(float(x), 3) for k, x in df[v].describe().items()} for v in n["parameters"]},
        "locations_sharing_identical_series": [sorted(v) for v in groups.values()],
        "api_failures": int((fdf["source"] == "nasa_power").sum()),
    }
    logger.info("NASA POWER: %d locations, %d obs, missing %% %s", m["locations_present"], m["total_observations"],
                m["missing_value_pct"])
    return m, rows


def validate_chirps(cfg, logger, window) -> tuple[dict, list[dict]]:
    c = cfg["chirps"]
    files = sorted(f for f in p(cfg, "raw_chirps").glob("*.zambia.*.nc") if ".part" not in f.name)
    if not files:
        return {"status": "missing"}, []
    start, end = pd.Timestamp(window["start"]), pd.Timestamp(window["end"])
    full = pd.date_range(start, end, freq="D")
    bounds = cfg["validation"]["bounds"]["chirps_precip"]
    times, per_year, flagged = [], {}, []
    total_px = total_nan = total_nodata = total_neg = 0
    grid = None
    for f in files:
        with xr.open_dataset(f) as ds:
            a = ds["precip"].values
            t = pd.DatetimeIndex(ds["time"].values)
            times.append(t)
            grid = grid or {"lat_min": float(ds.lat.min()), "lat_max": float(ds.lat.max()),
                            "lon_min": float(ds.lon.min()), "lon_max": float(ds.lon.max()),
                            "n_lat": int(ds.sizes["lat"]), "n_lon": int(ds.sizes["lon"])}
            nan = ~np.isfinite(a)
            nod = np.isin(a, c["nodata_values"])
            fin = np.where(nan | nod, np.nan, a)
            neg = fin < 0
            over = fin > bounds["max"]
            ext = fin > cfg["validation"]["extreme_rain_mm"]
            total_px += a.size
            total_nan += int(nan.sum()); total_nodata += int(nod.sum()); total_neg += int(neg.sum())
            per_year[f.name] = {"days": int(len(t)), "first": t.min().date().isoformat(),
                                "last": t.max().date().isoformat(), "nan_pixels": int(nan.sum()),
                                "nodata_pixels": int(nod.sum()), "negative_pixels": int(neg.sum()),
                                "pixels_over_max": int(over.sum()), "pixels_over_extreme": int(ext.sum()),
                                "max_mm": float(np.nanmax(fin)), "mean_mm": round(float(np.nanmean(fin)), 3)}
            for k in np.argwhere(over | neg):
                flagged.append({"date": t[k[0]].date(), "lat": float(ds.lat[k[1]]), "lon": float(ds.lon[k[2]]),
                                "value": float(a[tuple(k)]), "flag": "negative" if a[tuple(k)] < 0 else "above_max"})
            # extreme-but-plausible pixel-days: summarise by day rather than listing every pixel
            for i in np.where(ext.any(axis=(1, 2)))[0]:
                flagged.append({"date": t[i].date(), "lat": np.nan, "lon": np.nan, "value": float(np.nanmax(fin[i])),
                                "flag": f"extreme_check:{int(ext[i].sum())}_pixels>{cfg['validation']['extreme_rain_mm']}mm"})
    pd.DataFrame(flagged, columns=["date", "lat", "lon", "value", "flag"]).to_csv(
        ROOT / cfg["paths"]["reports"] / "chirps_flagged_values.csv", index=False)
    allt = times[0].append(times[1:]) if len(times) > 1 else times[0]
    missing_dates = full.difference(allt)
    man_path = p(cfg, "raw_chirps").parent / "chirps_manifest.csv"
    man = pd.read_csv(man_path) if man_path.exists() else pd.DataFrame(columns=["status"])
    pts_path = ROOT / cfg["paths"]["processed"] / "chirps_daily_at_locations.csv"
    pts = pd.read_csv(pts_path) if pts_path.exists() else None
    master = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv")
    inside = ((master["latitude"].between(grid["lat_min"], grid["lat_max"])) &
              (master["longitude"].between(grid["lon_min"], grid["lon_max"])))
    m = {
        "files": len(files), "date_range": [allt.min().date().isoformat(), allt.max().date().isoformat()],
        "days_expected": len(full), "days_present": int(allt.nunique()),
        "duplicate_dates": int(allt.duplicated().sum()),
        "missing_dates": [d.date().isoformat() for d in missing_dates][:200],
        "missing_dates_count": int(len(missing_dates)),
        "grid": grid, "bbox_requested": c["bbox"], "resolution_deg": 0.05,
        "pixel_days": int(total_px), "nan_pixel_days": total_nan, "nodata_pixel_days": total_nodata,
        "negative_pixel_days": total_neg,
        "missing_pixel_pct": round(100 * (total_nan + total_nodata) / total_px, 6) if total_px else None,
        "per_year": per_year,
        "download_status": vc(man["status"]) if len(man) else {},
        "locations_inside_grid": int(inside.sum()), "locations_outside_grid": int((~inside).sum()),
        "point_extraction_rows": int(len(pts)) if pts is not None else 0,
        "point_extraction_missing_pct": round(100 * pts["chirps_precip_mm"].isna().mean(), 4) if pts is not None else None,
        "point_extraction_duplicates": int(pts.duplicated(["location_id", "date"]).sum()) if pts is not None else None,
    }
    rows = [{"dataset": "chirps", "location_id": "GRID", "variable": "precip_days",
             "expected": len(full), "present": int(allt.nunique())},
            {"dataset": "chirps", "location_id": "GRID", "variable": "precip_pixel_days",
             "expected": int(total_px), "present": int(total_px - total_nan - total_nodata)}]
    if pts is not None:
        for loc, g in pts.groupby("location_id"):
            rows.append({"dataset": "chirps_points", "location_id": loc, "variable": "chirps_precip_mm",
                         "expected": len(full), "present": int(g["chirps_precip_mm"].notna().sum())})
    logger.info("CHIRPS: %d files, %d/%d days, missing pixel %% %s", m["files"], m["days_present"],
                m["days_expected"], m["missing_pixel_pct"])
    return m, rows


def cross_source(cfg) -> dict:
    """Sanity check only: monthly rainfall agreement between the two independent sources."""
    pp = ROOT / cfg["paths"]["raw_nasa_power"] / ".." / "nasa_power_daily.csv"
    cp = ROOT / cfg["paths"]["processed"] / "chirps_daily_at_locations.csv"
    if not (pp.exists() and cp.exists()):
        return {}
    a = pd.read_csv(pp, usecols=["location_id", "date", "PRECTOTCORR"], parse_dates=["date"])
    b = pd.read_csv(cp, usecols=["location_id", "date", "chirps_precip_mm"], parse_dates=["date"])
    j = a.merge(b, on=["location_id", "date"])
    if j.empty:
        return {}
    mon = j.groupby(["location_id", j["date"].dt.to_period("M")])[["PRECTOTCORR", "chirps_precip_mm"]].sum(min_count=1)
    r = mon.groupby(level=0).apply(lambda g: g["PRECTOTCORR"].corr(g["chirps_precip_mm"]))
    daily_r = j.groupby("location_id").apply(lambda g: g["PRECTOTCORR"].corr(g["chirps_precip_mm"]))
    return {"overlap_rows": int(len(j)),
            "monthly_total_corr_median": round(float(r.median()), 3), "monthly_total_corr_min": round(float(r.min()), 3),
            "daily_corr_median": round(float(daily_r.median()), 3),
            "mean_daily_mm_power": round(float(j["PRECTOTCORR"].mean()), 3),
            "mean_daily_mm_chirps": round(float(j["chirps_precip_mm"].mean()), 3)}


def checksums(cfg) -> dict:
    """Recompute sha256 of raw files and compare with the hash recorded at download time."""
    rows = []
    orig = ROOT / cfg["paths"]["raw_desinventar_original"]
    for z in orig.glob("*.zip"):
        prov = z.with_suffix(".provenance.json")
        rec = json.loads(prov.read_text(encoding="utf-8"))["sha256"] if prov.exists() else ""
        now = sha256_file(z)
        rows.append({"file": str(z.relative_to(ROOT)), "sha256": now, "recorded": rec, "match": now == rec})
    for meta in (ROOT / cfg["paths"]["raw_nasa_power"]).glob("*/*.meta.json"):
        f = meta.with_name(meta.name.replace(".meta.json", ".json"))
        rec = json.loads(meta.read_text(encoding="utf-8"))["sha256"]
        now = sha256_file(f)
        rows.append({"file": str(f.relative_to(ROOT)), "sha256": now, "recorded": rec, "match": now == rec})
    for f in (x for x in p(cfg, "raw_chirps").glob("*.nc") if ".part" not in x.name):
        rows.append({"file": str(f.relative_to(ROOT)), "sha256": sha256_file(f), "recorded": "", "match": ""})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / cfg["paths"]["reports"] / "raw_checksums.csv", index=False)
    chk = df[df["recorded"] != ""]
    return {"files_hashed": int(len(df)), "files_with_recorded_hash": int(len(chk)),
            "mismatches": chk.loc[~chk["match"].astype(bool), "file"].tolist()}


def failure_summary(cfg) -> dict:
    """Failed requests, split into those later recovered by a re-run and those still outstanding."""
    path = ROOT / cfg["paths"]["reports"] / "failed_requests.csv"
    if not path.exists():
        return {"total_failed_attempts": 0}
    f = pd.read_csv(path, dtype=str)
    out = {"total_failed_attempts": int(len(f))}
    ch = f[f["source"] == "chirps"]
    if len(ch):
        held = set()
        for nc in (f for f in p(cfg, "raw_chirps").glob("*.zambia.*.nc") if ".part" not in f.name):
            with xr.open_dataset(nc) as ds:
                held |= set(pd.to_datetime(ds["time"].values).strftime("%Y-%m-%d"))
        rec = ch["target"].isin(held)
        out["chirps"] = {"failed_attempts": int(len(ch)), "recovered_on_rerun": int(rec.sum()),
                         "outstanding_dates": sorted(set(ch.loc[~rec, "target"]))}
    pw = f[f["source"] == "nasa_power"]
    if len(pw):
        root = ROOT / cfg["paths"]["raw_nasa_power"]
        rec = pw["target"].map(lambda t: (root / t.split("__")[0] / f"{t}.json").exists())
        out["nasa_power"] = {"failed_attempts": int(len(pw)), "recovered_on_rerun": int(rec.sum()),
                             "outstanding": sorted(set(pw.loc[~rec, "target"]))}
    # other sources: recovered when the target file now exists anywhere under data/raw
    raw_root = ROOT / "data" / "raw"
    for src in sorted(set(f["source"]) - {"chirps", "nasa_power"}):
        sub = f[f["source"] == src]
        if src == "nasa_power_soil":
            root = ROOT / cfg["paths"]["raw_nasa_power_soil"]
            rec = sub["target"].map(lambda t: (root / t.split("__")[0] / f"{t}.json").exists())
        else:
            rec = sub["target"].map(lambda t: any(x for x in raw_root.rglob(f"{t}*") if ".part" not in x.name))
        out[src] = {"failed_attempts": int(len(sub)), "recovered_on_rerun": int(rec.sum()),
                    "outstanding": sorted(set(sub.loc[~rec, "target"]))}
    return out


def to_md(v: dict) -> str:
    d, n, c = v["desinventar"], v["nasa_power"], v["chirps"]
    L = [f"# Raw Data Validation Report", "", f"Generated {v['generated_utc']} by `scripts/validate_raw_data.py`. "
         "Values are flagged, never removed or changed.", "", "## DesInventar (FLOOD + FLASH FLOODS)", ""]
    for k in ["total_records_all_types", "flood_records", "flood_records_by_type", "date_precision",
              "date_range_day_precision", "date_range_all_valid_years", "suspicious_dates", "exact_duplicate_records",
              "probable_duplicate_records", "same_district_same_day_records", "missing_district",
              "records_missing_coordinates", "provinces_represented", "districts_represented",
              "invalid_numeric_fields", "location_resolution"]:
        L.append(f"- **{k}**: {d.get(k)}")
    L += ["", "## NASA POWER", ""]
    for k in ["locations_expected", "locations_present", "locations_missing", "date_range",
              "expected_days_per_location", "total_observations", "missing_value_pct", "duplicate_location_dates",
              "flagged_values", "api_failures"]:
        L.append(f"- **{k}**: {n.get(k)}")
    L.append(f"- **locations_incomplete_coverage**: {len(n.get('locations_incomplete_coverage', {}))}")
    L.append(f"- **groups of locations sharing an identical series**: {len(n.get('locations_sharing_identical_series', []))}")
    L += ["", "## CHIRPS v3.0", ""]
    for k in ["files", "date_range", "days_expected", "days_present", "missing_dates_count", "duplicate_dates", "grid",
              "missing_pixel_pct", "negative_pixel_days", "download_status", "locations_outside_grid",
              "point_extraction_missing_pct"]:
        L.append(f"- **{k}**: {c.get(k)}")
    L += ["", "## Failed requests", "", f"{v.get('failures')}"]
    L += ["", "## Cross-source rainfall sanity check", "", f"{v.get('cross_source')}", "",
          "## Raw file integrity", "", f"{v.get('checksums')}", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("validate", cfg)
    window = load_window(cfg)
    rep = p(cfg, "reports")
    d, r1 = validate_desinventar(cfg, logger)
    n, r2 = validate_power(cfg, logger, window)
    c, r3 = validate_chirps(cfg, logger, window)
    miss = pd.DataFrame(r1 + r2 + r3)
    miss["missing"] = miss["expected"] - miss["present"]
    miss["missing_pct"] = (100 * miss["missing"] / miss["expected"]).round(4)
    miss.to_csv(rep / "missing_data_report.csv", index=False)
    v = {"generated_utc": utc_now(), "window": window, "desinventar": d, "nasa_power": n, "chirps": c,
         "cross_source": cross_source(cfg), "checksums": checksums(cfg), "failures": failure_summary(cfg)}
    write_json(rep / "validation_report.json", v)
    (rep / "validation_report.md").write_text(to_md(v), encoding="utf-8")
    logger.info("Validation written to %s", (rep / "validation_report.md").relative_to(ROOT))


if __name__ == "__main__":
    main()
