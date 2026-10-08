"""Collect the GloFAS v4 river-network static maps (official JRC open data, CC BY 4.0, no login).

Source: "LISFLOOD static and parameter maps for GloFAS", dataset version 1.1.1 (for OS-LISFLOOD v4.x =
GloFAS v4.0), European Commission JRC, PID http://data.europa.eu/89h/68050d73-9c06-499c-a441-dc5053cb0c86
https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/LISFLOOD_static_and_parameter_maps_for_GloFAS/

Files (global, 0.05 deg = the GloFAS v4 grid):
  upArea_repaired.nc        accumulated upstream area of every pixel (m2)
  ldd_repaired.nc           local drainage direction (river network topology)
  chan_Global_03min.nc      channel mask (1 = river channel pixel)
Originals kept untouched in data/raw/glofas/static/original/; a Zambia window subset (values
unchanged) in data/raw/glofas/static/zambia_subset/. These define WHERE on the GloFAS grid each
district's rivers are, so discharge can be extracted on the river network rather than at centroids.

Usage
  python scripts/download_glofas_static.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, download_file, get_logger, load_config, p, utc_now  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("glofas_static", cfg)
    g = cfg["glofas"]
    root = p(cfg, "raw_glofas") / "static"
    orig, sub = root / "original", root / "zambia_subset"
    sub.mkdir(parents=True, exist_ok=True)
    b = g["area"]  # N, W, S, E
    failed = []
    for name in g["static_files"]:
        url = g["static_base_url"] + name
        f = download_file(cfg, logger, url, orig / name.rsplit("/", 1)[1], "glofas_static",
                          {"dataset": "LISFLOOD static and parameter maps for GloFAS", "dataset_version": "1.1.1 (GloFAS v4.x)",
                           "licence": "CC BY 4.0", "pid": "http://data.europa.eu/89h/68050d73-9c06-499c-a441-dc5053cb0c86"})
        if f is None:
            failed.append(name)
            continue
        out = sub / f.name.replace(".nc", "_zambia.nc")
        if out.exists():
            continue
        with xr.open_dataset(f) as ds:
            lat = [c for c in ds.coords if c.lower().startswith("lat")][0]
            lon = [c for c in ds.coords if c.lower().startswith("lon")][0]
            lat_slice = slice(b[0], b[2]) if ds[lat][0] > ds[lat][-1] else slice(b[2], b[0])
            s = ds.sel({lat: lat_slice, lon: slice(b[1], b[3])}).load()
        s.attrs.update(subset_note=f"window N{b[0]} W{b[1]} S{b[2]} E{b[3]} of {f.name}; values unchanged",
                       subset_created_utc=utc_now())
        s.to_netcdf(out)
        logger.info("Subset %s -> %s %s", f.name, out.name, dict(s.sizes))
    if failed:
        logger.error("GloFAS static maps missing (re-run to resume): %s", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
