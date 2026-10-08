"""Join static environmental / exposure rasters and vectors to the 101-district location master.

Every value is computed in TWO documented ways where both make sense, so Stage 3 can choose with
evidence instead of a silent default:
  *_point_*   value at the location-master coordinate (the same point used for NASA POWER/CHIRPS)
  *_district_* zonal statistic over the district polygon (DesInventar districts.shp, the polygons
               used to verify the location master; the 2 polygons whose code belongs to a differently
               named district are excluded, see reports/boundary_file_code_conflicts.csv)

Zonal rule: a raster cell belongs to a district when its CENTRE falls inside the polygon
(rasterio geometry_mask, all_touched=False). Areas and distances use ESRI:102022 (Africa Albers
Equal Area Conic). Degree-grid class fractions are weighted by cos(latitude) (true cell area).

Outputs (data/processed/, static district attributes; NOT an ML dataset, no target):
  district_terrain_hydrology.csv   HydroSHEDS DEM/slope, HydroRIVERS, HydroBASINS
  district_landcover.csv           ESA WorldCover 2021 class percentages + class at point
  exposure/worldpop_district_exposure.csv   WorldPop counts per district and year — EXPOSURE layer, kept
                                            in its own folder so it cannot drift into occurrence data
  derived_rasters/slope_15s_zambia.tif   slope (degrees) computed from the HydroSHEDS DEM

Usage
  python scripts/extract_district_environment.py [--only terrain|landcover|population]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.windows import from_bounds
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p, utc_now  # noqa: E402


def districts(cfg) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    master = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv", dtype={"district_code": str})
    master["district_code"] = master["location_id"].str.replace(cfg["location_master"]["location_id_prefix"], "", regex=False)
    g = gpd.read_file(ROOT / cfg["spatial"]["district_polygons"])
    if g.crs is None:
        g = g.set_crs("EPSG:4326")
    conf_path = ROOT / cfg["paths"]["reports"] / "boundary_file_code_conflicts.csv"
    if conf_path.exists():
        conf = pd.read_csv(conf_path, dtype=str)
        g = g[~(g["NAME"].isin(conf["NAME"]) & g["DATAB_DIST"].isin(conf["DATAB_DIST"]))]
    g = g.merge(master[["location_id", "district_code", "district", "latitude", "longitude"]],
                left_on="DATAB_DIST", right_on="district_code", how="inner")
    return g, master


def zonal(arr: np.ndarray, transform, geom, nodata=None) -> np.ndarray:
    m = geometry_mask([geom], out_shape=arr.shape, transform=transform, invert=True)
    v = arr[m]
    if nodata is not None:
        v = v[v != nodata]
    return v[np.isfinite(v)] if v.dtype.kind == "f" else v


def window_of(ds, geom, pad=0.02):
    x0, y0, x1, y1 = geom.bounds
    return from_bounds(x0 - pad, y0 - pad, x1 + pad, y1 + pad, ds.transform).round_offsets().round_lengths()


def slope_raster(dem_path: Path, out: Path, logger) -> Path:
    if out.exists():
        return out
    with rasterio.open(dem_path) as ds:
        z = ds.read(1).astype("float64")
        nod = ds.nodata
        tr, prof = ds.transform, ds.profile.copy()
    bad = (z == nod) if nod is not None else np.zeros_like(z, bool)
    z[bad] = np.nan
    lat = tr.f + tr.e * (np.arange(z.shape[0]) + 0.5)
    dy = abs(tr.e) * 110574.0                                   # metres per cell, north-south
    dx = (tr.a * 111320.0 * np.cos(np.radians(lat)))[:, None]   # metres per cell, east-west (varies with latitude)
    gy, gx = np.gradient(z)
    s = np.degrees(np.arctan(np.hypot(gx / dx, gy / dy))).astype("float32")
    s[bad] = np.nan
    prof.update(dtype="float32", nodata=np.nan, compress="deflate")
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(s, 1)
        dst.update_tags(source=str(dem_path.relative_to(ROOT)), method="central differences, geodesic cell size, degrees",
                        created_utc=utc_now())
    logger.info("Slope raster written: %s", out.relative_to(ROOT))
    return out


def terrain(cfg, logger, g: gpd.GeoDataFrame) -> pd.DataFrame:
    hs = cfg["hydrosheds"]
    sub = p(cfg, "raw_hydrosheds") / "zambia_subset"
    dem_path = sub / "dem_15s_zambia.tif"
    slope_path = slope_raster(dem_path, ROOT / cfg["paths"]["processed"] / "derived_rasters" / "slope_15s_zambia.tif", logger)
    rows = []
    with rasterio.open(dem_path) as dem, rasterio.open(slope_path) as slp:
        Z, S = dem.read(1), slp.read(1)
        nod = dem.nodata
        for d in g.itertuples():
            ez = zonal(Z, dem.transform, d.geometry, nod).astype(float)
            sz = zonal(S, slp.transform, d.geometry)
            r, c = dem.index(d.longitude, d.latitude)
            ep = float(Z[r, c]) if Z[r, c] != nod else np.nan
            rows.append({
                "location_id": d.location_id, "dem_cells": ez.size,
                "elev_point_m": ep, "slope_point_deg": float(S[r, c]),
                "elev_district_mean_m": ez.mean(), "elev_district_median_m": np.median(ez),
                "elev_district_min_m": ez.min(), "elev_district_max_m": ez.max(), "elev_district_std_m": ez.std(),
                "elev_district_p10_m": np.percentile(ez, 10), "elev_district_p90_m": np.percentile(ez, 90),
                "slope_district_mean_deg": sz.mean(), "slope_district_median_deg": np.median(sz),
                f"flat_fraction_slope_lt_{hs['flat_slope_deg']}deg": float((sz < hs["flat_slope_deg"]).mean()),
            })
    out = pd.DataFrame(rows)

    crs = cfg["spatial"]["projected_crs"]
    rivers = gpd.read_file(sub / "hydrorivers_zambia.gpkg").to_crs(crs)
    gp = g.to_crs(crs)
    pts = gpd.GeoSeries([Point(xy) for xy in zip(g["longitude"], g["latitude"])], crs="EPSG:4326").to_crs(crs)
    add = {d: {} for d in g["location_id"]}
    for thr in hs["river_upland_thresholds_km2"]:
        rv = rivers[rivers["UPLAND_SKM"] >= thr]
        idx = rv.sindex
        for loc, pt in zip(g["location_id"], pts):
            i = idx.nearest(pt, return_all=False)[1][0]
            add[loc][f"dist_point_to_river_upland_ge_{thr}km2_km"] = pt.distance(rv.geometry.iloc[i]) / 1000
            add[loc][f"upland_km2_of_nearest_river_ge_{thr}km2"] = rv["UPLAND_SKM"].iloc[i]
    # District-wide river proximity: distance from a regular ~2 km sample grid of points inside each
    # district to the nearest river of a given size (a single centroid distance can be unrepresentative).
    grid_step = 0.02
    for thr in (1000, 10000):
        rv = rivers[rivers["UPLAND_SKM"] >= thr]
        idx = rv.sindex
        for d, dp in zip(g.itertuples(), gp.geometry):
            x0, y0, x1, y1 = d.geometry.bounds
            xs, ys = np.meshgrid(np.arange(x0 + grid_step / 2, x1, grid_step), np.arange(y0 + grid_step / 2, y1, grid_step))
            sample = gpd.GeoSeries(gpd.points_from_xy(xs.ravel(), ys.ravel()), crs="EPSG:4326")
            sample = sample[sample.within(d.geometry)].to_crs(crs)
            if sample.empty:
                continue
            _, j = idx.nearest(sample, return_all=False)
            dist = sample.distance(rv.geometry.iloc[j].reset_index(drop=True).set_axis(sample.index)) / 1000
            add[d.location_id].update({
                f"dist_district_min_to_river_upland_ge_{thr}km2_km": dp.distance(rv.geometry.iloc[idx.nearest(dp)[1][0]]) / 1000,
                f"dist_district_mean_to_river_upland_ge_{thr}km2_km": float(dist.mean()),
                f"dist_district_median_to_river_upland_ge_{thr}km2_km": float(dist.median()),
                "river_proximity_sample_points": int(len(sample)),
            })
    major = rivers[rivers["UPLAND_SKM"] >= 1000]
    buf = major.buffer(hs["river_buffer_km"] * 1000).union_all()
    r100 = rivers[rivers["UPLAND_SKM"] >= 100]
    for d in gp.itertuples():
        inside = rivers[rivers.intersects(d.geometry)]
        clipped = r100[r100.intersects(d.geometry)].intersection(d.geometry)
        area_km2 = d.geometry.area / 1e6
        add[d.location_id].update({
            "district_area_km2": area_km2,
            "max_upland_km2_in_district": inside["UPLAND_SKM"].max() if len(inside) else np.nan,
            "max_dis_av_cms_in_district": inside["DIS_AV_CMS"].max() if len(inside) else np.nan,
            "river_density_upland_ge_100km2_km_per_km2": clipped.length.sum() / 1000 / area_km2,
            f"frac_district_within_{hs['river_buffer_km']}km_of_river_upland_ge_1000km2":
                d.geometry.intersection(buf).area / d.geometry.area,
        })
    for lev in ("04", "06"):
        b = gpd.read_file(sub / f"hybas_lev{lev}_zambia.gpkg")
        j = gpd.sjoin(gpd.GeoDataFrame({"location_id": g["location_id"].values},
                                       geometry=[Point(xy) for xy in zip(g["longitude"], g["latitude"])], crs="EPSG:4326"),
                      b[["HYBAS_ID", "MAIN_BAS", "SUB_AREA", "UP_AREA", "geometry"]], how="left", predicate="within")
        for r in j.itertuples():
            add[r.location_id][f"hybas_lev{lev}_id_point"] = r.HYBAS_ID
            if lev == "04":
                add[r.location_id]["hybas_main_basin_id_point"] = r.MAIN_BAS
            add[r.location_id][f"hybas_lev{lev}_up_area_km2_point"] = r.UP_AREA
        if lev == "04":
            ov = gpd.overlay(gp[["location_id", "geometry"]], b.to_crs(crs)[["HYBAS_ID", "geometry"]], how="intersection")
            ov["a"] = ov.area
            dom = ov.sort_values("a").groupby("location_id").tail(1)
            share = ov.groupby("location_id")["a"].transform("sum")
            ov["share"] = ov["a"] / share
            for r in dom.itertuples():
                add[r.location_id]["hybas_lev04_id_district_dominant"] = r.HYBAS_ID
                add[r.location_id]["hybas_lev04_district_dominant_share"] = float(ov.loc[r.Index, "share"])
    out = out.merge(pd.DataFrame.from_dict(add, orient="index").rename_axis("location_id").reset_index(), on="location_id")
    return out


def landcover(cfg, logger, g: gpd.GeoDataFrame) -> pd.DataFrame:
    wc = cfg["worldcover"]
    factor = 2 ** (wc["overview_level"] + 1)
    tiles = sorted((p(cfg, "raw_landcover") / f"worldcover_2021_v200_ov{factor}").glob("*.tif"))
    srcs = [rasterio.open(t) for t in tiles]
    classes = {int(k): v for k, v in wc["classes"].items()}
    rows = []
    try:
        for d in g.itertuples():
            x0, y0, x1, y1 = d.geometry.bounds
            use = [s for s in srcs if not (s.bounds.right <= x0 or s.bounds.left >= x1 or s.bounds.top <= y0 or s.bounds.bottom >= y1)]
            arr, tr = merge(use, bounds=(x0, y0, x1, y1), nodata=0)
            a = arr[0]
            m = geometry_mask([d.geometry], out_shape=a.shape, transform=tr, invert=True)
            lat = tr.f + tr.e * (np.arange(a.shape[0]) + 0.5)
            w = np.broadcast_to(np.cos(np.radians(lat))[:, None], a.shape)
            v, wv = a[m], w[m]
            valid = v != 0
            tot = wv[valid].sum()
            rec = {"location_id": d.location_id, "cells_sampled": int(valid.sum()),
                   "nodata_cells": int((~valid).sum()), "overview_factor": factor}
            for code, name in classes.items():
                rec[f"pct_{name}"] = 100 * wv[valid & (v == code)].sum() / tot if tot else np.nan
            pa, ptr = merge(use, bounds=(d.longitude - 0.001, d.latitude - 0.001, d.longitude + 0.001, d.latitude + 0.001), nodata=0)
            r, c = rasterio.transform.rowcol(ptr, d.longitude, d.latitude)
            rec["class_at_point"] = classes.get(int(pa[0][r, c]), "nodata")
            rows.append(rec)
    finally:
        for s in srcs:
            s.close()
    return pd.DataFrame(rows)


def population(cfg, logger, g: gpd.GeoDataFrame) -> pd.DataFrame:
    """Exposure layer (class C). Written to data/processed/exposure/, never into occurrence data."""
    import json
    rows = []
    crs = cfg["spatial"]["projected_crs"]
    area = g.to_crs(crs).area.values / 1e6
    for f in sorted(x for x in p(cfg, "raw_worldpop").glob("*.tif") if ".part" not in x.name):
        year = int(re.search(r"_(\d{4})_", f.name).group(1))
        prov = json.loads(f.with_name(f.name + ".provenance.json").read_text(encoding="utf-8"))
        with rasterio.open(f) as ds:
            A = ds.read(1, masked=True).filled(0).astype("float64")
            A[A < 0] = 0
            total = A.sum()
            assigned = 0.0
            for d, ar in zip(g.itertuples(), area):
                s = zonal(A, ds.transform, d.geometry).sum()
                assigned += s
                r, c = ds.index(d.longitude, d.latitude)
                rows.append({"location_id": d.location_id, "population_year": year, "population": s,
                             "population_density_per_km2": s / ar, "district_area_km2": ar,
                             "pop_in_point_cell": float(A[r, c]),
                             "source": "WorldPop, University of Southampton",
                             "version": f"{prov.get('title')} — unconstrained individual countries 2000-2020, 1 km, "
                                        f"not UN-adjusted; DOI {prov.get('doi')}",
                             "source_file": f.name, "role": "EXPOSURE ONLY - not a flood-occurrence predictor"})
        logger.info("WorldPop %d: raster total %.0f, assigned to districts %.0f (%.2f%%)", year, total, assigned,
                    100 * assigned / total)
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--only", choices=["terrain", "landcover", "population"])
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("district_env", cfg)
    g, master = districts(cfg)
    logger.info("District polygons joined to location master: %d of %d", len(g), len(master))
    proc = ROOT / cfg["paths"]["processed"]
    jobs = {"terrain": (terrain, "district_terrain_hydrology.csv"), "landcover": (landcover, "district_landcover.csv"),
            "population": (population, "exposure/worldpop_district_exposure.csv")}
    for name, (fn, fname) in jobs.items():
        if args.only and name != args.only:
            continue
        try:
            df = fn(cfg, logger, g)
        except (FileNotFoundError, StopIteration, ValueError, rasterio.errors.RasterioIOError) as e:
            logger.error("%s not extracted (inputs missing?): %s", name, e)
            continue
        df["created_utc"] = utc_now()
        (proc / fname).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(proc / fname, index=False)
        logger.info("%s: %d rows -> %s", name, len(df), fname)


if __name__ == "__main__":
    main()
