"""Extract district-level GloFAS v4.0 HISTORICAL (reanalysis) series from the downloaded GRIB2 files.

Method (decided in reports/glofas_extraction_method_comparison.md):
  river discharge            value at the district's MAIN-RIVER cell (C: largest upstream area in the
                             district) and, as a sensitivity variant, at the NEAREST significant-river cell (D)
  runoff, soil wetness index MEAN over all cells whose centre lies in the district (B, zonal)
Values are copied, never filled or interpolated; missing stays missing.

Input : data/raw/glofas/historical/<variable>/*.grib2 (from scripts/download_glofas.py)
        data/processed/hydrology/glofas_district_extraction_points.csv
Output: data/processed/hydrology/glofas_historical_district_daily.csv
        (location_id, date, discharge_main_river_m3s, discharge_nearest_river_m3s,
         runoff_district_mean, soil_wetness_index_district_mean, product_type, source_files)
These are reanalysis values: use only dates <= prediction date t. Reforecasts are handled separately.

Usage
  python scripts/extract_glofas.py [--input-dir DIR]   (--input-dir is for testing on other folders)
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
from _common import ROOT, get_logger, load_config, utc_now  # noqa: E402
from extract_district_environment import districts  # noqa: E402

COLS = {"river_discharge_in_the_last_24_hours": "discharge", "runoff_water_equivalent": "runoff_district_mean",
        "soil_wetness_index": "soil_wetness_index_district_mean"}


def open_any(f: Path) -> xr.Dataset:
    if f.suffix in (".grib2", ".grib"):
        return xr.open_dataset(f, engine="cfgrib", backend_kwargs={"indexpath": ""})
    return xr.open_dataset(f)


def as_grid(ds: xr.Dataset) -> xr.DataArray:
    v = next(n for n in ds.data_vars if ds[n].ndim >= 2)
    da = ds[v]
    rename = {c: "lat" for c in da.dims if c.lower().startswith("lat")} | {c: "lon" for c in da.dims if c.lower().startswith("lon")}
    da = da.rename(rename)
    # GRIB "in the last 24 hours" fields are stamped at the END of the averaging period (valid_time =
    # time + step). Label each value with the day it describes, i.e. the period START = valid_time - step,
    # otherwise every value would be shifted one day late (a temporal-alignment error).
    if "valid_time" in da.coords and "step" in da.coords:
        start = pd.DatetimeIndex(np.atleast_1d(da["valid_time"].values)) - pd.to_timedelta(np.atleast_1d(da["step"].values))
        tdim = next((d for d in da.dims if d in ("time", "valid_time")), None)
        if tdim:
            da = da.assign_coords({tdim: start}).rename({tdim: "time"}) if tdim != "time" else da.assign_coords(time=start)
            return da.sortby("lat", ascending=False).transpose("time", "lat", "lon")
    tdim = next((d for d in da.dims if d in ("time", "valid_time")), None)
    if tdim is None and "valid_time" in da.coords:
        da = da.expand_dims(time=[pd.Timestamp(da["valid_time"].values)])
    elif tdim and tdim != "time":
        da = da.rename({tdim: "time"})
    if "time" not in da.dims:
        da = da.expand_dims(time=[pd.Timestamp(ds["time"].values)])
    return da.sortby("lat", ascending=False).transpose("time", "lat", "lon")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--input-dir")
    ap.add_argument("--output")
    ap.add_argument("--points", help="extraction-points CSV (default: data/processed/hydrology/glofas_district_extraction_points.csv)")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("extract_glofas", cfg)
    src = Path(args.input_dir) if args.input_dir else ROOT / cfg["paths"]["raw_glofas"] / "historical"
    pts = pd.read_csv(args.points or ROOT / cfg["paths"]["processed"] / "hydrology" / "glofas_district_extraction_points.csv")
    g, _ = districts(cfg)
    frames = {}
    for var, col in COLS.items():
        files = sorted(x for x in (src / var).glob("*.grib2") if ".part" not in x.name) + sorted((src / var).glob("*.nc"))
        if not files:
            logger.warning("No files for %s in %s", var, src / var)
            continue
        parts = []
        for f in files:
            with open_any(f) as ds:
                da = as_grid(ds).load()
            lat, lon = da["lat"].values, da["lon"].values
            res = abs(float(lon[1] - lon[0]))
            ix = lambda a, x: int(np.abs(a - x).argmin())  # noqa: E731
            t = pd.DatetimeIndex(da["time"].values).normalize()
            if var.startswith("river_discharge"):
                for r in pts.itertuples():
                    parts.append(pd.DataFrame({"location_id": r.location_id, "date": t,
                                               "discharge_main_river_m3s": da.values[:, ix(lat, r.C_main_river_lat), ix(lon, r.C_main_river_lon)],
                                               "discharge_nearest_river_m3s": da.values[:, ix(lat, r.D_nearest_river_lat), ix(lon, r.D_nearest_river_lon)],
                                               "source_file": f.name}))
            else:
                tr = from_origin(lon[0] - res / 2, lat[0] + res / 2, res, res)
                for d in g.itertuples():
                    m = geometry_mask([d.geometry], out_shape=(len(lat), len(lon)), transform=tr, invert=True)
                    vals = np.nanmean(np.where(m[None], da.values, np.nan), axis=(1, 2)) if m.any() else np.full(len(t), np.nan)
                    parts.append(pd.DataFrame({"location_id": d.location_id, "date": t, col: vals, "source_file": f.name}))
        frames[var] = pd.concat(parts, ignore_index=True)
        logger.info("%s: %d files -> %d rows", var, len(files), len(frames[var]))
    if not frames:
        logger.error("No GloFAS historical files found — run scripts/download_glofas.py first (needs EWDS credentials)")
        sys.exit(1)
    out = None
    for var, df in frames.items():
        df = df.rename(columns={"source_file": f"source_file_{COLS[var]}"})
        out = df if out is None else out.merge(df, on=["location_id", "date"], how="outer")
    out = out.sort_values(["location_id", "date"])
    dup = int(out.duplicated(["location_id", "date"]).sum())
    if dup:
        logger.warning("%d duplicate location-dates (overlapping files) — kept for inspection, not dropped", dup)
    out["extracted_utc"] = utc_now()
    dest = Path(args.output) if args.output else ROOT / cfg["paths"]["processed"] / "hydrology" / "glofas_historical_district_daily.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False)
    logger.info("Wrote %s: %d rows, %d locations, %s -> %s", dest, len(out), out["location_id"].nunique(),
                out["date"].min(), out["date"].max())


if __name__ == "__main__":
    main()
