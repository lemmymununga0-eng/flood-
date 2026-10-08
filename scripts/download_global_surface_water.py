"""Collect JRC Global Surface Water (GSW) v1.4 'occurrence' for Zambia and summarise it per district.

What it adds: an OBSERVED (Landsat, 1984-2021) frequency with which every 30 m cell was water. Cells
that are water only part of the time are floodplains / seasonal wetlands — empirical flood-proneness
that neither WorldCover (one year) nor HydroSHEDS (terrain) provides.

Source: Pekel, J.-F., Cottam, A., Gorelick, N., Belward, A.S. (2016) High-resolution mapping of global
surface water and its long-term changes. Nature 540, 418-422. Data: EC JRC / Google,
https://global-surface-water.appspot.com/download (tiles on Google Cloud Storage, version 1.4, 2021).
Licence: Copernicus programme / EC JRC — free use with attribution.

Raw tiles (10 x 10 degree, named by their north-west corner) kept unchanged in
data/raw/other/global_surface_water/. District summary -> data/processed/environmental/district_surface_water.csv

Temporal caveat: occurrence aggregates 1984-2021, i.e. partly AFTER many flood events. It is a
static susceptibility descriptor (optional), never a dated observation.

Usage
  python scripts/download_global_surface_water.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, download_file, get_logger, load_config, p, utc_now  # noqa: E402

URL = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_{tile}v1_4_2021.tif"


def tiles_for(bounds) -> list[str]:
    x0, y0, x1, y1 = bounds
    out = []
    for top in range(math.ceil(y1 / 10) * 10, math.floor(y0 / 10) * 10, -10):
        for left in range(math.floor(x0 / 10) * 10, math.ceil(x1 / 10) * 10, 10):
            ns = f"{abs(top)}{'N' if top > 0 else 'S'}" if top != 0 else "0N"
            out.append(f"{abs(left)}{'E' if left >= 0 else 'W'}_{ns}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("gsw", cfg)
    raw = p(cfg, "raw_other") / "global_surface_water"
    raw.mkdir(parents=True, exist_ok=True)
    g = gpd.read_file(ROOT / cfg["spatial"]["district_polygons"])
    g = g.set_crs("EPSG:4326") if g.crs is None else g
    tiles = tiles_for(g.total_bounds)
    logger.info("GSW occurrence tiles needed: %s", tiles)
    files, missing = [], []
    for t in tiles:
        f = download_file(cfg, logger, URL.format(tile=t), raw / f"occurrence_{t}v1_4_2021.tif", "global_surface_water",
                          {"product": "JRC Global Surface Water occurrence", "version": "1.4 (2021)",
                           "citation": "Pekel et al. (2016) Nature 540:418-422"})
        (files if f else missing).append(f or t)
    if missing:
        logger.error("GSW incomplete; missing tiles %s (re-run to resume)", missing)
        sys.exit(1)

    # ---- district summary (cells whose centre is inside the polygon; cos-latitude area weighting) ----
    from extract_district_environment import districts
    gd, _ = districts(cfg)
    srcs = [rasterio.open(f) for f in files]
    rows = []
    try:
        for d in gd.itertuples():
            x0, y0, x1, y1 = d.geometry.bounds
            arr, tr = merge(srcs, bounds=(x0, y0, x1, y1), nodata=255)
            a = arr[0]
            m = geometry_mask([d.geometry], out_shape=a.shape, transform=tr, invert=True)
            lat = tr.f + tr.e * (np.arange(a.shape[0]) + 0.5)
            w = np.broadcast_to(np.cos(np.radians(lat))[:, None], a.shape)
            valid = m & (a != 255)
            v, wv = a[valid].astype(np.int16), w[valid]
            tot = wv.sum()
            rows.append({"location_id": d.location_id, "cells": int(valid.sum()),
                         "pct_ever_water": 100 * wv[v > 0].sum() / tot,
                         "pct_intermittent_water_1_to_74": 100 * wv[(v > 0) & (v < 75)].sum() / tot,
                         "pct_permanent_water_ge_75": 100 * wv[v >= 75].sum() / tot,
                         "mean_occurrence_pct": float((v * wv).sum() / tot)})
    finally:
        for s in srcs:
            s.close()
    out = ROOT / cfg["paths"]["processed"] / "environmental" / "district_surface_water.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).assign(source="JRC Global Surface Water v1.4 occurrence (1984-2021)", created_utc=utc_now())
    df.to_csv(out, index=False)
    logger.info("GSW district summary: %d districts -> %s", len(df), out.relative_to(ROOT))


if __name__ == "__main__":
    main()
