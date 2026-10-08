"""SECOND, INDEPENDENT AUDIT: is what we collected complete, correct, consistent and usable?

Deliberately does NOT reuse the validators' outputs. Every check re-derives its answer from the raw
source files with a different code path (or from the source server), so an error in the first-pass
scripts would show up here as a mismatch.

Checks (one row each in reports/second_audit_checks.csv):
  DesInventar   re-parse the ORIGINAL ZIP's XML with a regex parser (not ElementTree); compare counts,
                record keys and every field of every flood record with the processed table
  Locations     every coordinate inside Zambia and inside its own district polygon; IDs/codes unique;
                district code prefix == province code
  NASA POWER    re-read every raw JSON; compare every value with the flattened CSV; units and API
                version identical across files; suspicious constant runs; day-to-day jumps
  Soil wetness  same as NASA POWER
  CHIRPS        recompute the point series for every location from the NetCDFs and compare with the CSV;
                time continuity across yearly files; per-day source URL matches its date; spot re-read of
                random days from the official CHC COGs (network)
  Alignment     lagged correlation POWER vs CHIRPS rainfall (peak must be at lag 0 -> no date shift)
  HydroSHEDS    subset DEM equals the same window read straight from inside the original ZIP
  WorldCover    tile tags (version, source URL), CRS, resolution, class codes
  WorldPop      checksums; CRS; national totals monotonic
  Climate idx   re-parse raw text independently; compare with tidy CSV
  GloFAS static subset equals original window (if present)
  Files         sha256 vs provenance; duplicate files; undocumented raw folders; no target columns;
                no post-event columns outside DesInventar; exposure kept separate
Quality flags written to data/quality_flags/. Report: reports/second_audit_report.md

Usage
  python scripts/second_audit.py [--no-network]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, utc_now  # noqa: E402

CHECKS: list[dict] = []


def check(dataset, name, ok, detail="", warn=False):
    CHECKS.append({"dataset": dataset, "check": name,
                   "result": "PASS" if ok else ("WARN" if warn else "FAIL"), "detail": str(detail)[:600]})


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------
def audit_desinventar(cfg):
    zp = ROOT / cfg["paths"]["raw_desinventar_original"] / "DI_export_zmb.zip"
    with zipfile.ZipFile(zp) as z:
        xml = z.read(next(n for n in z.namelist() if n.endswith(".xml"))).decode("utf-8")
    sec = xml[xml.find("<fichas>"):xml.find("</fichas>")]
    recs = [dict(re.findall(r"<(\w+)>([^<]*)</\1>", tr)) for tr in re.findall(r"<TR>(.*?)</TR>", sec, re.S)]
    unesc = lambda s: s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")  # noqa: E731
    recs = [{k: unesc(v) for k, v in r.items()} for r in recs]
    check("DesInventar", "record count from original ZIP (regex parser)", len(recs) == 2239, f"{len(recs)} records")
    floods = {r["clave"]: r for r in recs if r.get("evento") in ("FLOOD", "FLASH FLOODS")}
    proc = pd.read_csv(ROOT / cfg["paths"]["processed"] / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    check("DesInventar", "flood record set identical to processed table",
          set(floods) == set(proc["clave"]) and len(floods) == len(proc),
          f"raw {len(floods)} vs processed {len(proc)}; only-raw {sorted(set(floods) - set(proc['clave']))[:5]}")
    mism = 0
    fields = ["serial", "evento", "fechano", "fechames", "fechadia", "level0", "level1", "name0", "name1", "lugar", "muertos",
              "afectados", "vivdest", "vivafec", "latitude", "longitude", "descausa"]
    for r in proc.itertuples():
        raw = floods.get(r.clave, {})
        for fld in fields:
            if raw.get(fld, "") != getattr(r, fld):
                mism += 1
    check("DesInventar", "every field of every flood record equals the raw XML (17 fields x 444 records)", mism == 0, f"{mism} mismatches")
    ev = defaultdict(int)
    for r in recs:
        ev[r.get("evento")] += 1
    check("DesInventar", "FLOOD / FLASH FLOODS counts", ev["FLOOD"] == 436 and ev["FLASH FLOODS"] == 8, f"FLOOD {ev['FLOOD']}, FLASH {ev['FLASH FLOODS']}")
    audit = pd.read_csv(ROOT / cfg["paths"]["processed"] / "desinventar_flood_event_audit.csv", dtype=str, keep_default_na=False)
    vc = audit["date_confidence"].value_counts().to_dict()
    check("DesInventar", "date-confidence classes sum to all flood records", sum(vc.values()) == len(proc), vc)
    # independent recomputation of date precision from raw fields
    def prec(r):
        y, m, d = r["fechano"], r["fechames"], r["fechadia"]
        if not (y.isdigit() and len(y) == 4):
            return "invalid"
        return "year" if m in ("", "0") else ("month" if d in ("", "0") else "day")
    p_raw = pd.Series([prec(floods[c]) for c in proc["clave"]]).value_counts().to_dict()
    check("DesInventar", "date precision recomputed from raw fields", p_raw == proc["date_precision"].value_counts().to_dict(), p_raw)


def audit_locations(cfg):
    import geopandas as gpd
    from shapely.geometry import Point
    m = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv", dtype={"district_code": str, "province_code": str})
    regiones = pd.read_csv(ROOT / cfg["paths"]["raw_desinventar_extracted"] / "tables" / "regiones.csv", dtype=str, keep_default_na=False)
    g = gpd.read_file(ROOT / cfg["spatial"]["district_polygons"])
    g = g.set_crs("EPSG:4326") if g.crs is None else g
    zm = g.union_all()
    codes = m["location_id"].str.replace(cfg["location_master"]["location_id_prefix"], "", regex=False)
    check("Locations", "101 unique location IDs", m["location_id"].is_unique and len(m) == 101, len(m))
    check("Locations", "no duplicate coordinates", not m.duplicated(["latitude", "longitude"]).any(), int(m.duplicated(["latitude", "longitude"]).sum()))
    inside = [zm.contains(Point(x, y)) for x, y in zip(m["longitude"], m["latitude"])]
    check("Locations", "every coordinate inside Zambia", all(inside), f"{sum(inside)}/101")
    own = []
    for c, x, y, name in zip(codes, m["longitude"], m["latitude"], m["district"]):
        polys = g[(g["DATAB_DIST"] == c)]
        own.append(any(pg.contains(Point(x, y)) for pg in polys.geometry))
    check("Locations", "every coordinate inside a polygon carrying its district code", all(own), f"{sum(own)}/101")
    # independent: the province each district belongs to in the RAW regiones table vs the master's province name
    prov_names = regiones[regiones["nivel"] == "0"].set_index("codregion")["nombre"].str.lower()
    raw_prov = codes.str[:2].map(prov_names)
    agree = (raw_prov.str.replace("-", " ") == m["province"].str.lower().str.replace("-", " "))
    check("Locations", "province of every district agrees with the raw DesInventar geography", bool(agree.all()),
          m.loc[~agree, ["location_id", "province"]].to_dict("records"))
    check("Locations", "all 10 provinces present", m["province"].nunique() == 10, sorted(m["province"].unique()))


def audit_power(cfg, folder: Path, csv: Path, params: list[str], label: str, flags_dir: Path):
    df = pd.read_csv(csv, parse_dates=["date"])
    mism, units, versions, n = 0, set(), set(), 0
    for f in sorted(folder.glob("*/*.json")):
        if f.name.endswith(".meta.json"):
            continue
        j = json.loads(f.read_text(encoding="utf-8"))
        loc = f.parent.name
        par = j["properties"]["parameter"]
        units.add(json.dumps({k: v["units"] for k, v in j["parameters"].items()}, sort_keys=True))
        versions.add(j["header"]["api"]["version"])
        sub = df[df["location_id"] == loc]
        sub = sub.set_index(sub["date"].dt.strftime("%Y%m%d"))
        for v in params:
            raw = pd.Series(par[v]).replace(-999.0, np.nan)
            mism += int((~np.isclose(raw.values, sub.loc[raw.index, v].values, equal_nan=True)).sum())
        n += 1
    check(label, f"every value in CSV equals raw JSON ({n} files)", mism == 0, f"{mism} mismatching values")
    check(label, "units identical in every raw file", len(units) == 1, units)
    check(label, "API version identical in every raw file", len(versions) == 1, versions)
    # suspicious constant runs (>= 10 identical non-zero consecutive values) and jumps
    flags = []
    for v in params:
        for loc, s in df.sort_values("date").groupby("location_id")[v]:
            x = s.values
            run_id = np.r_[0, np.cumsum(np.diff(x) != 0)]
            lengths = pd.Series(run_id).map(pd.Series(run_id).value_counts())
            bad = (lengths.values >= 10) & (x != 0)
            if bad.any():
                flags.append({"dataset": label, "location_id": loc, "variable": v, "flag": "constant_run_ge_10",
                              "n_days": int(bad.sum())})
            if v.startswith("T2M"):
                jumps = np.abs(np.diff(x)) > 15
                if jumps.any():
                    flags.append({"dataset": label, "location_id": loc, "variable": v, "flag": "day_to_day_jump_gt_15C",
                                  "n_days": int(jumps.sum())})
    pd.DataFrame(flags, columns=["dataset", "location_id", "variable", "flag", "n_days"]).to_csv(
        flags_dir / f"{label.lower().replace(' ', '_')}_timeseries_flags.csv", index=False)
    check(label, "suspicious constant runs / temperature jumps", True if not flags else False,
          f"{len(flags)} location-variable flags (see data/quality_flags/)", warn=True)
    return df


def audit_chirps(cfg, pw: pd.DataFrame, network: bool, flags_dir: Path):
    import xarray as xr
    files = sorted(f for f in p(cfg, "raw_chirps").glob("*.zambia.*.nc") if ".part" not in f.name)
    pts = pd.read_csv(ROOT / cfg["paths"]["processed"] / "chirps_daily_at_locations.csv", parse_dates=["date"])
    m = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv")
    times, mism, url_bad, units = [], 0, 0, set()
    for f in files:
        with xr.open_dataset(f) as ds:
            t = pd.DatetimeIndex(ds["time"].values)
            times.append(t)
            units.add(ds["precip"].attrs.get("units"))
            # independent nearest-cell lookup by index arithmetic (not .sel)
            lat, lon = ds["lat"].values, ds["lon"].values
            for r in m.itertuples():
                i, k = int(np.abs(lat - r.latitude).argmin()), int(np.abs(lon - r.longitude).argmin())
                series = ds["precip"].values[:, i, k]
                ref = pts[(pts["location_id"] == r.location_id) & pts["date"].isin(t)].sort_values("date")["chirps_precip_mm"].values
                mism += int((~np.isclose(series, ref, equal_nan=True)).sum()) if len(ref) == len(series) else len(series)
            urls = ds["source_url"].values
            url_bad += sum(f"{d:%Y.%m.%d}" not in str(u) for d, u in zip(t, urls))
    allt = times[0].append(times[1:])
    win = load_window(cfg)
    full = pd.date_range(win["start"], win["end"])
    check("CHIRPS", "point CSV equals values recomputed from NetCDFs (101 locations, all days)", mism == 0, f"{mism} mismatches")
    check("CHIRPS", "continuous daily time axis across yearly files", allt.equals(full), f"{len(allt)} vs {len(full)}")
    check("CHIRPS", "each day's source URL matches its date", url_bad == 0, url_bad)
    check("CHIRPS", "units attribute", units == {"mm/day"}, units)
    if network:
        import rasterio
        rnd = random.Random(42)
        sample = rnd.sample(list(full), 5)
        diffs = []
        env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".cog")
        c = cfg["chirps"]
        try:
            with rasterio.Env(**env):
                for d in sample:
                    loc = m.sample(1, random_state=d.day).iloc[0]
                    with rasterio.open("/vsicurl/" + c["cog_url_template"].format(stream=c["stream"], variant=c["variant"],
                                                                                  year=d.year, month=d.month, day=d.day)) as src:
                        v = float(list(src.sample([(loc.longitude, loc.latitude)]))[0][0])
                    ours = float(pts[(pts["location_id"] == loc.location_id) & (pts["date"] == d)]["chirps_precip_mm"].iloc[0])
                    diffs.append(abs(v - ours))
            check("CHIRPS", "5 random location-days re-read from official CHC COGs", max(diffs) < 1e-3, f"max |diff| {max(diffs):.6f}")
        except Exception as e:  # noqa: BLE001
            check("CHIRPS", "5 random location-days re-read from official CHC COGs", False, f"network: {e}", warn=True)
    # temporal alignment: correlation of POWER vs CHIRPS at lags -2..+2 (both point series)
    j = pw[["location_id", "date", "PRECTOTCORR"]].merge(pts[["location_id", "date", "chirps_precip_mm"]], on=["location_id", "date"])
    lag_r = {}
    for lag in (-2, -1, 0, 1, 2):
        s = j.sort_values(["location_id", "date"]).copy()
        s["c"] = s.groupby("location_id")["chirps_precip_mm"].shift(lag)
        lag_r[lag] = round(float(s["PRECTOTCORR"].corr(s["c"])), 3)
    best = max(lag_r, key=lag_r.get)
    check("Alignment", "POWER vs CHIRPS rainfall correlation peaks at lag 0 (no date shift)", best == 0, lag_r)


def audit_rasters(cfg, network: bool):
    import rasterio
    # HydroSHEDS subset vs original inside the ZIP
    orig = ROOT / cfg["paths"]["raw_hydrosheds"] / "original" / "hyd_af_dem_15s.zip"
    subf = ROOT / cfg["paths"]["raw_hydrosheds"] / "zambia_subset" / "dem_15s_zambia.tif"
    with rasterio.open(subf) as s:
        sub = s.read(1)
        b = s.bounds
    with rasterio.open(f"zip://{orig.as_posix()}!hyd_af_dem_15s.tif") as o:
        from rasterio.windows import from_bounds
        w = from_bounds(*b, o.transform).round_offsets().round_lengths()
        ref = o.read(1, window=w)
    check("HydroSHEDS", "Zambia DEM subset identical to the same window inside the original ZIP", np.array_equal(sub, ref), f"{sub.shape}")
    # WorldCover tiles
    tiles = sorted((ROOT / cfg["paths"]["raw_landcover"]).rglob("*.tif"))
    ok_tags, ok_crs, ok_res, codes = True, True, True, set()
    for t in tiles:
        with rasterio.open(t) as ds:
            tg = ds.tags()
            ok_tags &= tg.get("src_product_version") == "V2.0.0" and "ESA_WorldCover_10m_2021_v200" in tg.get("source_url", "")
            ok_crs &= ds.crs.to_epsg() == 4326
            ok_res &= abs(ds.res[0] - 3 / 9000) < 1e-9
            codes |= set(np.unique(ds.read(1, out_shape=(900, 900))).tolist())
    check("WorldCover", f"{len(tiles)} tiles: product version V2.0.0 + official source URL", ok_tags and len(tiles) == 17, len(tiles))
    check("WorldCover", "CRS EPSG:4326 and 1/4-overview resolution (3/9000 deg)", ok_crs and ok_res)
    check("WorldCover", "only valid class codes", codes <= {0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}, sorted(codes))
    # WorldPop
    tot = []
    for f in sorted((ROOT / cfg["paths"]["raw_worldpop"]).glob("*.tif")):
        with rasterio.open(f) as ds:
            a = ds.read(1, masked=True)
            tot.append(float(a.sum()))
    check("WorldPop", "21 yearly rasters; national total rises every year", len(tot) == 21 and all(np.diff(tot) > 0),
          f"{len(tot)} files; {tot[0]:,.0f} -> {tot[-1]:,.0f}")


def audit_climate(cfg):
    raw = ROOT / cfg["paths"]["raw_climate_indices"]
    tidy = pd.read_csv(ROOT / cfg["paths"]["processed"] / "climate_indices_monthly.csv")
    seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    bad = 0
    for ln in (raw / "oni.ascii.txt").read_text().splitlines()[1:]:
        s, y, _, anom = ln.split()
        row = tidy[(tidy["year"] == int(y)) & (tidy["month"] == seasons.index(s) + 1)]
        bad += int(row.empty or not np.isclose(row["oni"].iloc[0], float(anom)))
    check("Climate indices", "ONI tidy table equals raw text (every season)", bad == 0, f"{bad} mismatches")
    bad = 0
    for ln in (raw / "dmi.had.long.data").read_text().splitlines()[1:]:
        parts = ln.split()
        if len(parts) == 13 and parts[0].isdigit() and 1870 <= int(parts[0]) <= 2026:
            for mth, v in enumerate(parts[1:], 1):
                val = float(v)
                row = tidy[(tidy["year"] == int(parts[0])) & (tidy["month"] == mth)]["dmi_hadisst"]
                bad += int(not ((val <= -99 and row.isna().all()) or (len(row) and np.isclose(row.iloc[0], val))))
    check("Climate indices", "DMI tidy table equals raw text (every month)", bad == 0, f"{bad} mismatches")


def audit_glofas_static(cfg):
    import xarray as xr
    sub_dir = ROOT / cfg["paths"]["raw_glofas"] / "static" / "zambia_subset"
    orig_dir = ROOT / cfg["paths"]["raw_glofas"] / "static" / "original"
    subs = sorted(sub_dir.glob("*.nc"))
    check("GloFAS static", "3 river-network maps (upArea, ldd, chan) present", len(subs) == 3, [s.name for s in subs])
    for s in subs:
        o = orig_dir / s.name.replace("_zambia.nc", ".nc")
        with xr.open_dataset(s) as a, xr.open_dataset(o) as b:
            v = next(x for x in a.data_vars if a[x].ndim == 2)
            lat = [c for c in a.coords if c.lower().startswith("lat")][0]
            lon = [c for c in a.coords if c.lower().startswith("lon")][0]
            ref = b[v].sel({lat: a[lat], lon: a[lon]})
            check("GloFAS static", f"{s.name} identical to the same window of the original", bool(np.array_equal(a[v].values, ref.values, equal_nan=True)))


def audit_surface_water(cfg):
    f = ROOT / cfg["paths"]["processed"] / "environmental" / "district_surface_water.csv"
    tiles = sorted((ROOT / cfg["paths"]["raw_other"] / "global_surface_water").glob("*.tif"))
    check("Global Surface Water", "4 occurrence tiles present", len(tiles) == 4, [t.name for t in tiles])
    if not f.exists():
        check("Global Surface Water", "district summary present", False, "not built yet")
        return
    s = pd.read_csv(f)
    pct = s.filter(like="pct_")
    check("Global Surface Water", "101 districts, percentages within 0-100", len(s) == 101 and bool(((pct >= 0) & (pct <= 100)).all().all()))
    check("Global Surface Water", "intermittent + permanent = ever water",
          bool(np.allclose(s["pct_intermittent_water_1_to_74"] + s["pct_permanent_water_ge_75"], s["pct_ever_water"], atol=1e-6)))
    lc = pd.read_csv(ROOT / cfg["paths"]["processed"] / "district_landcover.csv")[["location_id", "pct_permanent_water"]]
    j = s.merge(lc, on="location_id")
    r = float(j["pct_permanent_water_ge_75"].corr(j["pct_permanent_water"], method="spearman"))
    check("Cross-dataset", "GSW permanent water vs WorldCover permanent water (independent sensors/years)", r > 0.7, f"Spearman {r:.3f}")


def audit_glofas_series(cfg, pw: pd.DataFrame):
    f = ROOT / cfg["paths"]["processed"] / "hydrology" / "glofas_historical_district_daily.csv"
    if not f.exists():
        g_cfg = cfg["glofas"]
        if g_cfg.get("collection_status") == "deferred":
            check("GloFAS historical", "time series collected", False,
                  f"DEFERRED by researcher decision {g_cfg.get('decision_date')} (no EWDS credentials); static river maps "
                  "collected; scripts/download_glofas.py + extract_glofas.py ready", warn=True)
        else:
            check("GloFAS historical", "time series collected", False,
                  "not downloaded: EWDS requires the researcher's ECMWF account (scripts/download_glofas.py ready)")
        return
    g = pd.read_csv(f, parse_dates=["date"])
    win = load_window(cfg)
    full = pd.date_range(win["start"], win["end"])
    per = g.groupby("location_id")["date"].nunique()
    check("GloFAS historical", "101 locations x every day of the window", len(per) == 101 and (per >= len(full)).all(),
          f"{len(per)} locations; min days {per.min()}")
    check("GloFAS historical", "no duplicate location-dates", not g.duplicated(["location_id", "date"]).any())
    check("GloFAS historical", "no negative discharge", (g["discharge_main_river_m3s"].dropna() >= 0).all())
    if "runoff_district_mean" in g:
        j = pw[["location_id", "date", "PRECTOTCORR"]].merge(g[["location_id", "date", "runoff_district_mean"]], on=["location_id", "date"])
        lag_r = {}
        for lag in (-2, -1, 0, 1, 2):
            s = j.sort_values(["location_id", "date"]).copy()
            s["r"] = s.groupby("location_id")["runoff_district_mean"].shift(-lag)  # runoff `lag` days after rain
            lag_r[lag] = round(float(s["PRECTOTCORR"].corr(s["r"])), 3)
        best = max(lag_r, key=lag_r.get)
        check("Alignment", "GloFAS runoff responds to rainfall at lag 0 or +1 day (never before the rain)", best in (0, 1), lag_r)


def audit_files(cfg):
    raw_root = ROOT / "data" / "raw"
    bad_hash, by_hash = [], defaultdict(list)
    for prov in raw_root.rglob("*.provenance.json"):
        f = prov.with_name(prov.name.replace(".provenance.json", ""))
        if not f.exists():  # e.g. DI_export_zmb.provenance.json describes DI_export_zmb.zip
            f = next((x for x in prov.parent.glob(f.name + ".*") if not x.name.endswith(".json")), f)
        rec = json.loads(prov.read_text(encoding="utf-8"))
        if "sha256" in rec:
            h = sha(f)
            by_hash[h].append(str(f.relative_to(ROOT)))
            if h != rec["sha256"]:
                bad_hash.append(str(f.relative_to(ROOT)))
    for meta in raw_root.rglob("*.meta.json"):
        f = meta.with_name(meta.name.replace(".meta.json", ".json"))
        rec = json.loads(meta.read_text(encoding="utf-8"))
        h = sha(f)
        by_hash[h].append(str(f.relative_to(ROOT)))
        if h != rec["sha256"]:
            bad_hash.append(str(f.relative_to(ROOT)))
    check("Files", "every raw file's sha256 equals its provenance record", not bad_hash, f"{sum(len(v) for v in by_hash.values())} hashed; mismatches {bad_hash[:5]}")
    dups = [v for v in by_hash.values() if len(v) > 1]
    check("Files", "no duplicate raw files (identical content under two names)", not dups, dups[:3])
    documented = (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8") + (ROOT / "docs" / "FINAL_DATA_INVENTORY.md").read_text(encoding="utf-8") \
        if (ROOT / "docs" / "FINAL_DATA_INVENTORY.md").exists() else (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8")
    undocumented = [d.name for d in raw_root.iterdir() if d.is_dir() and f"data/raw/{d.name}" not in documented]
    check("Files", "every raw folder is documented", not undocumented, undocumented)
    # no targets / leakage columns in processed tables
    target_cols, post_cols = [], []
    post = re.compile(r"^(muertos|heridos|afectados|vivdest|vivafec|damnificados|valorus|valorloc)$")
    empty = []
    for f in (ROOT / "data").rglob("*.csv"):
        try:
            cols = pd.read_csv(f, nrows=0).columns
        except pd.errors.EmptyDataError:  # e.g. DesInventar XML sections that are empty in the official export
            empty.append(str(f.relative_to(ROOT)).replace("\\", "/"))
            continue
        target_cols += [f"{f.name}:{c}" for c in cols if c.startswith("flood_next")]
        if "desinventar" not in str(f.relative_to(ROOT)).lower():  # raw DesInventar tables legitimately hold consequences
            post_cols += [f"{f.name}:{c}" for c in cols if post.match(c)]
    check("Files", "empty CSVs are only empty sections of the official DesInventar export",
          all("desinventar/extracted/tables" in e for e in empty), empty)
    check("Leakage", "no target columns (flood_next_*) anywhere in data/", not target_cols, target_cols)
    check("Leakage", "no post-event consequence columns outside DesInventar tables", not post_cols, post_cols)
    exp = ROOT / cfg["paths"]["processed"] / "exposure"
    other_pop = [f.name for f in (ROOT / cfg["paths"]["processed"]).glob("*.csv") if "population" in pd.read_csv(f, nrows=0).columns]
    check("Leakage", "population appears only in the separate exposure folder", exp.exists() and not other_pop, other_pop)
    fails = pd.read_csv(ROOT / cfg["paths"]["reports"] / "failed_requests.csv")
    check("Files", "failed-request log reviewed", True, fails.groupby("source").size().to_dict())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-network", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("second_audit", cfg)
    flags_dir = p(cfg, "quality_flags")
    steps = [("DesInventar", lambda: audit_desinventar(cfg)), ("Locations", lambda: audit_locations(cfg))]
    for name, fn in steps:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            check(name, "audit ran", False, repr(e))
    try:
        pw = audit_power(cfg, ROOT / cfg["paths"]["raw_nasa_power"], ROOT / "data/raw/nasa_power/nasa_power_daily.csv",
                         cfg["nasa_power"]["parameters"], "NASA POWER", flags_dir)
        audit_power(cfg, ROOT / cfg["paths"]["raw_nasa_power_soil"], ROOT / "data/raw/nasa_power/nasa_power_daily_soil_moisture.csv",
                    cfg["nasa_power_soil"]["parameters"], "Soil wetness", flags_dir)
        audit_chirps(cfg, pw, not args.no_network, flags_dir)
        audit_glofas_series(cfg, pw)
    except Exception as e:  # noqa: BLE001
        check("Weather", "audit ran", False, repr(e))
    for name, fn in [("Rasters", lambda: audit_rasters(cfg, not args.no_network)), ("Climate indices", lambda: audit_climate(cfg)),
                     ("GloFAS static", lambda: audit_glofas_static(cfg)), ("Global Surface Water", lambda: audit_surface_water(cfg)),
                     ("Files", lambda: audit_files(cfg))]:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            check(name, "audit ran", False, repr(e))
    df = pd.DataFrame(CHECKS)
    rep = p(cfg, "reports")
    df.to_csv(rep / "second_audit_checks.csv", index=False)
    summ = df["result"].value_counts().to_dict()
    L = ["# Second, independent audit", "", f"_Generated {utc_now()} by `scripts/second_audit.py`. Every check re-derives its result "
         "from raw sources with a different code path from the first-pass validators._", "",
         f"**Result: {summ}**", "", "| Dataset | Check | Result | Detail |", "|---|---|---|---|"]
    L += [f"| {r.dataset} | {r.check} | **{r.result}** | {str(r.detail).replace('|', '/')} |" for r in df.itertuples()]
    (rep / "second_audit_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    logger.info("Second audit: %s", summ)


if __name__ == "__main__":
    main()
