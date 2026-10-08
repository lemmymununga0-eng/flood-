"""Decide WHERE on the GloFAS 0.05 deg grid each district's hydrology should be read, and document why.

Compared methods (all computed, so the choice is evidence-based):
  A  centroid      the GloFAS cell containing the district point
  B  zonal         all cells whose centre lies inside the district polygon (mean of the field)
  C  main river    the cell inside the district with the LARGEST upstream area (main river through it)
  D  nearest river the cell with upstream area >= threshold nearest to the district point
Discharge only has meaning ON the river network, so A/B are unsuitable for discharge; runoff and soil
wetness are areal quantities, so B is the natural choice for them. The table produced here is what
scripts/extract_glofas.py will use once the GloFAS time series are downloaded.

Cross-check: GloFAS upstream area at C vs HydroRIVERS' largest upstream area in the same district
(independent river networks) — large disagreement would reveal a grid/coordinate error.

Outputs: data/processed/hydrology/glofas_district_extraction_points.csv,
         reports/glofas_extraction_method_comparison.md
Usage
  python scripts/build_glofas_extraction_points.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from rasterio.features import geometry_mask
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p, utc_now  # noqa: E402
from extract_district_environment import districts  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("glofas_points", cfg)
    sub = ROOT / cfg["paths"]["raw_glofas"] / "static" / "zambia_subset"
    with xr.open_dataset(sub / "upArea_repaired_zambia.nc") as ds:
        v = next(n for n in ds.data_vars if ds[n].ndim == 2)  # skip the 'crs' placeholder variable
        lat_n = [c for c in ds.coords if c.lower().startswith("lat")][0]
        lon_n = [c for c in ds.coords if c.lower().startswith("lon")][0]
        ds = ds.sortby(lat_n, ascending=False)
        up = ds[v].values / 1e6  # m2 -> km2
        lat, lon = ds[lat_n].values, ds[lon_n].values
    with xr.open_dataset(sub / "chan_Global_03min_zambia.nc") as cs:
        cs = cs.sortby([c for c in cs.coords if c.lower().startswith("lat")][0], ascending=False)
        chan = cs[next(n for n in cs.data_vars if cs[n].ndim == 2)].values
    res = abs(lon[1] - lon[0])
    tr = from_origin(lon[0] - res / 2, lat[0] + res / 2, res, res)
    thr = cfg["glofas"]["river_upstream_min_km2"]
    g, _ = districts(cfg)
    terr = pd.read_csv(ROOT / cfg["paths"]["processed"] / "district_terrain_hydrology.csv").set_index("location_id")
    LAT, LON = np.meshgrid(lat, lon, indexing="ij")
    rows = []
    for d in g.itertuples():
        i, k = int(np.abs(lat - d.latitude).argmin()), int(np.abs(lon - d.longitude).argmin())
        m = geometry_mask([d.geometry], out_shape=up.shape, transform=tr, invert=True)
        ups = np.where(m & np.isfinite(up), up, -1)
        ci, ck = np.unravel_index(int(ups.argmax()), up.shape)
        riv = np.isfinite(up) & (up >= thr)
        dist_km = np.hypot((LAT - d.latitude) * 110.57, (LON - d.longitude) * 111.32 * np.cos(np.radians(d.latitude)))
        dist_km = np.where(riv, dist_km, np.inf)
        ni, nk = np.unravel_index(int(dist_km.argmin()), up.shape)
        rows.append({
            "location_id": d.location_id, "district": d.district,
            "A_centroid_lat": lat[i], "A_centroid_lon": lon[k], "A_upstream_km2": float(up[i, k]), "A_on_significant_river": bool(up[i, k] >= thr),
            "B_zonal_cells": int(m.sum()),
            "C_main_river_lat": lat[ci], "C_main_river_lon": lon[ck], "C_upstream_km2": float(up[ci, ck]),
            "D_nearest_river_lat": lat[ni], "D_nearest_river_lon": lon[nk], "D_upstream_km2": float(up[ni, nk]),
            "D_distance_km": float(dist_km[ni, nk]), "D_inside_district": bool(m[ni, nk]),
            "hydrorivers_max_upland_km2": float(terr.loc[d.location_id, "max_upland_km2_in_district"]),
        })
    df = pd.DataFrame(rows)
    df["C_vs_hydrorivers_ratio"] = df["C_upstream_km2"] / df["hydrorivers_max_upland_km2"]
    out = ROOT / cfg["paths"]["processed"] / "hydrology" / "glofas_district_extraction_points.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.assign(created_utc=utc_now()).to_csv(out, index=False)

    lr = np.log10(df[["C_upstream_km2", "hydrorivers_max_upland_km2"]]).corr().iloc[0, 1]
    within = ((df["C_vs_hydrorivers_ratio"] > 0.5) & (df["C_vs_hydrorivers_ratio"] < 2)).mean()
    L = ["# GloFAS extraction-method comparison", "", f"_Generated {utc_now()} by `scripts/build_glofas_extraction_points.py` "
         "from the official GloFAS v4 static maps (upArea, chan)._", "",
         "| Method | What it samples | Median upstream area (km²) | Notes |", "|---|---|---:|---|",
         f"| A centroid | cell at the district point | {df['A_upstream_km2'].median():,.0f} | on a river with ≥{thr:,} km² upstream in only {df['A_on_significant_river'].mean():.0%} of districts — usually a minor stream cell |",
         f"| B zonal | all {int(df['B_zonal_cells'].median())} (median) cells in the district | — | mixes river and hillslope cells: meaningless for discharge, appropriate for runoff and soil wetness |",
         f"| C main river | largest-upstream cell in the district | {df['C_upstream_km2'].median():,.0f} | the river that carries the district's (and upstream) flood water |",
         f"| D nearest river ≥{thr:,} km² | nearest significant river to the point | {df['D_upstream_km2'].median():,.0f} | median {df['D_distance_km'].median():.1f} km away; inside the district in {df['D_inside_district'].mean():.0%} of cases |", "",
         "## Decision", "",
         "- **River discharge → C (main river in district)**, with D as a sensitivity variant. Discharge exists only on the river "
         "network; a centroid cell is rarely a river cell, and averaging discharge over a district is physically meaningless.",
         "- **Runoff water equivalent and soil wetness index → B (district zonal mean)** — areal fluxes/states.",
         "- A is recorded only for transparency.",
         f"- Note: the GloFAS channel mask (`chan`) marks {100 * float((chan == 1).mean()):.0f}% of cells in the window as channel "
         "(LISFLOOD routes water through a channel in every cell), so it cannot separate rivers from hillslopes; "
         "upstream area is used instead.", "",
         "## Cross-check against HydroRIVERS (independent river network)", "",
         f"- log10 correlation of GloFAS upstream area at C vs HydroRIVERS' largest upstream area in the district: **{lr:.3f}**",
         f"- Districts where the two agree within a factor of 2: **{within:.0%}**",
         "- Disagreements are expected where a district only touches a large river at its boundary (grid cells vs vector "
         "lines) — see `C_vs_hydrorivers_ratio` in the CSV.", ""]
    (p(cfg, "reports") / "glofas_extraction_method_comparison.md").write_text("\n".join(L), encoding="utf-8")
    logger.info("GloFAS extraction points: %d districts; centroid on significant river %.0f%%; C vs HydroRIVERS log-r %.3f, within x2 %.0f%%",
                len(df), 100 * df["A_on_significant_river"].mean(), lr, 100 * within)
    flags = df.loc[(df["C_vs_hydrorivers_ratio"] < 0.5) | (df["C_vs_hydrorivers_ratio"] > 2),
                   ["location_id", "district", "C_upstream_km2", "hydrorivers_max_upland_km2", "C_vs_hydrorivers_ratio"]]
    flags.assign(flag="glofas_vs_hydrorivers_upstream_area_differs_gt_x2",
                 note="grid-cell vs vector-line boundary effect; check main-river pixel before using discharge").to_csv(
        p(cfg, "quality_flags") / "glofas_extraction_point_flags.csv", index=False)


if __name__ == "__main__":
    main()
