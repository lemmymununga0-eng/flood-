"""Validate the Stage 2 environmental / context / exposure data -> reports/environmental_data_validation_report.md

Covers HydroSHEDS (DEM, slope, HydroRIVERS, HydroBASINS), ESA WorldCover, WorldPop, NASA POWER
soil wetness, climate indices and the DFO flood archive, plus the district-level extractions.
Checks: file integrity (sha256 vs provenance), CRS/bounds, coverage of all 101 districts, missing
values, impossible values, plausibility ranges and unit consistency. Nothing is modified.

Usage
  python scripts/validate_environmental_data.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, sha256_file, utc_now, write_json  # noqa: E402


def integrity(folder: Path) -> list[dict]:
    rows = []
    for prov in sorted(folder.rglob("*.provenance.json")):
        f = prov.with_name(prov.name.replace(".provenance.json", ""))
        rec = json.loads(prov.read_text(encoding="utf-8"))
        ok = f.exists() and sha256_file(f) == rec.get("sha256")
        rows.append({"file": str(f.relative_to(ROOT)).replace("\\", "/"), "bytes": f.stat().st_size if f.exists() else 0,
                     "retrieved_utc": rec.get("retrieved_utc"), "sha256_matches_provenance": ok})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("validate_env", cfg)
    proc = ROOT / cfg["paths"]["processed"]
    rep = p(cfg, "reports")
    master = pd.read_csv(proc / "location_master.csv")
    locs = set(master["location_id"])
    S: dict = {"generated_utc": utc_now()}
    L = ["# Environmental Data Validation Report", "",
         f"_Generated {S['generated_utc']} by `scripts/validate_environmental_data.py`. Values are flagged, never altered._", ""]

    def section(name, status, lines):
        S[name] = {"status": status}
        L.extend([f"## {name}", "", f"**Status: {status}**", "", *lines, ""])

    # ---- HydroSHEDS ------------------------------------------------------------------------------
    hs_root = p(cfg, "raw_hydrosheds")
    sub = hs_root / "zambia_subset"
    integ = integrity(hs_root / "original")
    lines = [f"- Original archives: {len(integ)} of {len(cfg['hydrosheds']['files'])} expected; "
             f"sha256 verified: {sum(r['sha256_matches_provenance'] for r in integ)}"]
    expected = ["dem_15s_zambia.tif", "hydrorivers_zambia.gpkg", "hybas_lev04_zambia.gpkg", "hybas_lev06_zambia.gpkg"]
    have = [e for e in expected if (sub / e).exists()]
    lines.append(f"- Zambia subsets present: {have}")
    if (sub / "dem_15s_zambia.tif").exists():
        with rasterio.open(sub / "dem_15s_zambia.tif") as ds:
            z = ds.read(1, masked=True)
            lines += [f"- DEM: CRS {ds.crs.to_string()}, {ds.width}×{ds.height} cells, resolution {ds.res[0]:.6f}° (~{ds.res[0] * 111.32 * 1000:.0f} m), "
                      f"bounds {tuple(round(b, 3) for b in ds.bounds)}, nodata {ds.nodata}",
                      f"- DEM elevation range in window: {z.min()}–{z.max()} m; nodata cells: {int(z.mask.sum())}"]
            S["dem"] = {"min": float(z.min()), "max": float(z.max()), "nodata_cells": int(z.mask.sum())}
    terr_path = proc / "district_terrain_hydrology.csv"
    if terr_path.exists():
        t = pd.read_csv(terr_path)
        num = t.select_dtypes("number")
        lines += [f"- District terrain/hydrology table: {len(t)} rows; districts missing: {sorted(locs - set(t['location_id'])) or 'none'}; "
                  f"cells with missing values: {int(num.isna().sum().sum())}",
                  f"- District mean elevation: {t['elev_district_mean_m'].min():.0f}–{t['elev_district_mean_m'].max():.0f} m "
                  f"(Zambia's lowest point is ~329 m on the Zambezi and highest ~2,300 m in the Mafinga Hills)",
                  f"- District minimum / maximum elevation overall: {t['elev_district_min_m'].min():.0f} / {t['elev_district_max_m'].max():.0f} m",
                  f"- Mean slope: {t['slope_district_mean_deg'].min():.2f}–{t['slope_district_mean_deg'].max():.2f}°; "
                  f"flat fraction: {t.filter(like='flat_fraction').iloc[:, 0].min():.2f}–{t.filter(like='flat_fraction').iloc[:, 0].max():.2f}",
                  f"- Point-to-river distance (upland ≥1,000 km²): median {t['dist_point_to_river_upland_ge_1000km2_km'].median():.1f} km, "
                  f"max {t['dist_point_to_river_upland_ge_1000km2_km'].max():.1f} km",
                  f"- Max upstream area within a district: {t['max_upland_km2_in_district'].min():.0f}–{t['max_upland_km2_in_district'].max():.0f} km²",
                  f"- District area check (equal-area projection): {t['district_area_km2'].sum():,.0f} km² summed "
                  f"(Zambia ≈ 752,600 km²; the 2 excluded boundary-conflict polygons account for part of any shortfall)",
                  f"- Points without a HydroBASINS level-6 basin: {int(t['hybas_lev06_id_point'].isna().sum())}"]
        bad = t[(t["elev_district_min_m"] < 300) | (t["elev_district_max_m"] > 2400)]
        lines.append(f"- Elevations outside 300–2,400 m: {len(bad)} districts")
        S["terrain"] = {"rows": len(t), "missing_cells": int(num.isna().sum().sum()), "out_of_range": len(bad)}
    status = "COMPLETE" if len(have) == 4 and terr_path.exists() and len(integ) == 4 else ("PARTIAL" if have or integ else "MISSING")
    section("HydroSHEDS (terrain and hydrology)", status, lines)

    # ---- WorldCover --------------------------------------------------------------------------------
    wc = cfg["worldcover"]
    factor = 2 ** (wc["overview_level"] + 1)
    tiles = sorted((p(cfg, "raw_landcover") / f"worldcover_2021_v200_ov{factor}").glob("*.tif"))
    tiles = [t for t in tiles if ".part" not in t.name]
    lines = [f"- Tiles present: {len(tiles)} ({', '.join(t.stem for t in tiles)})"]
    valid_codes = set(int(k) for k in wc["classes"]) | {0}
    bad_codes = set()
    for t in tiles:
        with rasterio.open(t) as ds:
            a = ds.read(1, out_shape=(ds.height // 10, ds.width // 10))  # decimated read is enough to check codes
            bad_codes |= set(np.unique(a).tolist()) - valid_codes
    lines.append(f"- Invalid class codes found: {sorted(bad_codes) or 'none'} (valid: {sorted(valid_codes)})")
    lc_path = proc / "district_landcover.csv"
    if lc_path.exists():
        lc = pd.read_csv(lc_path)
        pct = lc.filter(like="pct_")
        lines += [f"- District land-cover table: {len(lc)} rows; districts missing: {sorted(locs - set(lc['location_id'])) or 'none'}",
                  f"- Percentages sum to 100 ± 0.01 in {int((pct.sum(axis=1).sub(100).abs() < 0.01).sum())} of {len(lc)} districts",
                  f"- No-data cells inside districts: {int(lc['nodata_cells'].sum())} of {int(lc['cells_sampled'].sum() + lc['nodata_cells'].sum())}",
                  "- Zambia-wide mean of district percentages: " + ", ".join(f"{c[4:]} {v:.1f}%" for c, v in pct.mean().sort_values(ascending=False).items() if v > 0.05)]
    status = "COMPLETE" if tiles and not bad_codes and lc_path.exists() else ("PARTIAL" if tiles else "MISSING")
    section("ESA WorldCover 2021", status, lines)

    # ---- WorldPop ----------------------------------------------------------------------------------
    integ = integrity(p(cfg, "raw_worldpop"))
    y0, y1 = cfg["worldpop"]["years"]
    lines = [f"- Yearly rasters: {len(integ)} of {y1 - y0 + 1}; sha256 verified: {sum(r['sha256_matches_provenance'] for r in integ)}"]
    pop_path = proc / "exposure" / "worldpop_district_exposure.csv"
    if pop_path.exists():
        pop = pd.read_csv(pop_path)
        tot = pop.groupby("population_year")["population"].sum()
        lines += [f"- Exposure table `data/processed/exposure/worldpop_district_exposure.csv`: {len(pop)} rows, years "
                  f"{pop['population_year'].min()}–{pop['population_year'].max()}, districts per year "
                  f"{pop.groupby('population_year')['location_id'].nunique().min()}",
                  "- National total assigned to districts: " + ", ".join(f"{y}: {v / 1e6:.2f} M" for y, v in tot.items() if y in (2000, 2005, 2010, 2015, 2020)),
                  f"- Negative or missing populations: {int((pop['population'] < 0).sum() + pop['population'].isna().sum())}",
                  "- Unit: estimated people per ~1 km cell (WorldPop unconstrained, not UN-adjusted); district values are sums of cells whose centre lies in the district."]
    status = "COMPLETE" if len(integ) == y1 - y0 + 1 and pop_path.exists() else ("PARTIAL" if integ else "MISSING")
    section("WorldPop population (exposure layer)", status, lines)

    # ---- NASA POWER soil wetness ---------------------------------------------------------------------
    sp = ROOT / cfg["paths"]["raw_nasa_power"] / ".." / "nasa_power_daily_soil_moisture.csv"
    lines = []
    if sp.exists():
        sm = pd.read_csv(sp, parse_dates=["date"])
        win = load_window(cfg)
        exp = len(pd.date_range(win["start"], win["end"]))
        params = cfg["nasa_power_soil"]["parameters"]
        lines += [f"- Locations: {sm['location_id'].nunique()} of {len(locs)}; rows {len(sm)} (expected {exp * len(locs)})",
                  f"- Date range: {sm['date'].min().date()} → {sm['date'].max().date()}; duplicate location-dates: {int(sm.duplicated(['location_id', 'date']).sum())}",
                  "- Missing %: " + ", ".join(f"{v} {100 * sm[v].isna().mean():.3f}%" for v in params),
                  "- Range (unit: soil wetness fraction 0–1, NASA POWER/MERRA-2): " + ", ".join(f"{v} {sm[v].min():.2f}–{sm[v].max():.2f}" for v in params),
                  f"- Values outside [0, 1]: {int(sum(((sm[v] < 0) | (sm[v] > 1)).sum() for v in params))}"]
        # Overlap with antecedent rainfall (data characterisation, not a model test): how much of the
        # soil-wetness signal is already carried by trailing rainfall sums from the same provider?
        wx = pd.read_csv(ROOT / cfg["paths"]["raw_nasa_power"] / ".." / "nasa_power_daily.csv",
                         usecols=["location_id", "date", "PRECTOTCORR"], parse_dates=["date"]).sort_values(["location_id", "date"])
        for k in (7, 30, 90):
            wx[f"rain_{k}d"] = wx.groupby("location_id")["PRECTOTCORR"].transform(lambda s: s.rolling(k, min_periods=k).sum())
        jm = sm.merge(wx, on=["location_id", "date"])
        corr = {v: {f"{k}d": jm.groupby("location_id").apply(lambda g: g[v].corr(g[f"rain_{k}d"], method="spearman"),
                                                              include_groups=False).median() for k in (7, 30, 90)}
                for v in params}
        lines.append("- Median (over districts) Spearman correlation with trailing NASA POWER rainfall: " + "; ".join(
            f"{v}: " + ", ".join(f"{k} {r:.2f}" for k, r in c.items()) for v, c in corr.items()))
        lines.append("- Interpretation: strong correlation with 30–90-day rainfall means soil wetness largely re-expresses "
                     "antecedent rainfall from the same reanalysis; it is kept as an OPTIONAL EXPERIMENT, not a core feature.")
        S["soil_rain_overlap_spearman"] = {v: {k: round(float(r), 3) for k, r in c.items()} for v, c in corr.items()}
        ok = sm["location_id"].nunique() == len(locs) and len(sm) == exp * len(locs)
        status = "COMPLETE" if ok else "PARTIAL"
    else:
        status = "MISSING"
    section("Soil wetness (NASA POWER GWETTOP/GWETROOT/GWETPROF — optional experiment)", status, lines)

    # ---- Climate indices ---------------------------------------------------------------------------
    cpath = proc / "climate_indices_monthly.csv"
    lines = []
    if cpath.exists():
        ci = pd.read_csv(cpath)
        win = load_window(cfg)
        y_start = pd.Timestamp(win["start"]).year - 1
        sub_ci = ci[(ci["year"] >= y_start) & ((ci["year"] < 2026) | (ci["month"] <= 6))]
        for col in ["oni", "nino34_anom", "dmi_hadisst"]:
            s = sub_ci[col]
            lines.append(f"- {col}: {int(s.notna().sum())} of {len(s)} months present from {y_start}-01 to 2026-06; "
                         f"range {s.min():.2f} to {s.max():.2f}; latest value {ci.loc[ci[col].notna(), ['year', 'month']].iloc[-1].tolist()}")
        w = pd.read_csv(proc / "climate_iod_weekly_bom.csv", parse_dates=["week_start", "week_end"])
        lines.append(f"- BoM weekly IOD: {len(w)} weeks, {w['week_start'].min().date()} → {w['week_end'].max().date()} "
                     "(starts 2008 — too short to be the only IOD source; NOAA PSL monthly DMI covers the full window)")
        status = "COMPLETE"
    else:
        status = "MISSING"
    section("Climate indices (ONI, Niño 3.4, DMI/IOD)", status, lines)

    # ---- DFO ---------------------------------------------------------------------------------------
    dfo = proc / "dfo_zambia_events.csv"
    if dfo.exists():
        d = pd.read_csv(dfo)
        began = pd.to_datetime(d.get("Began"), errors="coerce")
        lines = [f"- Zambia-related DFO events: {len(d)}; dates {began.min().date() if began.notna().any() else '?'} → "
                 f"{began.max().date() if began.notna().any() else '?'}",
                 "- Use: independent cross-check of DesInventar dates (validation only, not training labels)."]
        status = "COMPLETE"
    else:
        lines = ["- floodobservatory.colorado.edu was unreachable from this machine during collection; "
                 "`scripts/download_flood_observations.py` retries and resumes."]
        status = "MISSING"
    section("Dartmouth Flood Observatory archive (optional validation)", status, lines)

    (rep / "environmental_data_validation_report.md").write_text("\n".join(L), encoding="utf-8")
    write_json(rep / "environmental_data_validation_summary.json", S)
    logger.info("Environmental validation: %s", {k: v["status"] for k, v in S.items() if isinstance(v, dict) and "status" in v})


if __name__ == "__main__":
    main()
