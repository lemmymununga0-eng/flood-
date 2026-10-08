"""Collect HydroSHEDS v1 terrain/hydrology for Zambia (official downloads, Africa extent).

Downloaded (original ZIPs kept untouched in data/raw/hydrosheds/original/):
  hyd_af_dem_15s.zip            void-filled DEM, 15 arc-second (~460 m)
  HydroRIVERS_v10_af_shp.zip    river network (reaches with upstream area >= 10 km2), incl. UPLAND_SKM
  hybas_af_lev04_v1c.zip        HydroBASINS level 4 (large sub-basins)
  hybas_af_lev06_v1c.zip        HydroBASINS level 6 (medium sub-basins)
Not downloaded, by design: flow-direction and flow-accumulation rasters. HydroRIVERS already
carries each reach's upstream catchment area (UPLAND_SKM), derived from those rasters, which is
what a district join needs; the 130 MB accumulation raster would add nothing for 101 districts.

The ZIPs are unzipped to data/raw/hydrosheds/extracted/ only while a subset is being built, then that
temporary folder is removed (it would duplicate the preserved originals).
Zambia subsets (values unchanged, for fast reuse) in data/raw/hydrosheds/zambia_subset/:
  dem_15s_zambia.tif, hydrorivers_zambia.gpkg, hybas_lev04_zambia.gpkg, hybas_lev06_zambia.gpkg

Usage
  python scripts/download_hydrosheds.py
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, download_file, get_logger, load_config, p, utc_now  # noqa: E402

PAD = 0.25  # degrees of padding around Zambia so edge districts keep their neighbourhood


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("hydrosheds", cfg)
    hs = cfg["hydrosheds"]
    root = p(cfg, "raw_hydrosheds")
    orig, ext, sub = root / "original", root / "extracted", root / "zambia_subset"
    for d in (orig, ext, sub):
        d.mkdir(exist_ok=True)

    got = {}
    for key, url in hs["files"].items():
        got[key] = download_file(cfg, logger, url, orig / url.rsplit("/", 1)[1], "hydrosheds",
                                 {"product": key, "version": "HydroSHEDS v1 / HydroRIVERS v1.0 / HydroBASINS v1c"})
    missing = [k for k, v in got.items() if v is None]
    if missing:
        logger.error("Missing HydroSHEDS products (re-run to resume): %s", missing)

    subset_name = {"dem_15s": "dem_15s_zambia.tif", "hydrorivers": "hydrorivers_zambia.gpkg",
                   "hydrobasins_lev04": "hybas_lev04_zambia.gpkg", "hydrobasins_lev06": "hybas_lev06_zambia.gpkg"}
    for key, z in got.items():
        if z is None or (sub / subset_name[key]).exists():
            continue  # unzip only what is needed to (re)build a missing subset
        with zipfile.ZipFile(z) as zz:
            target = ext / z.stem
            if not target.exists():
                zz.extractall(target)
                logger.info("Extracted %s", z.name)

    b = cfg["location_master"]["zambia_bbox"]
    bb = (b["lon_min"] - PAD, b["lat_min"] - PAD, b["lon_max"] + PAD, b["lat_max"] + PAD)
    if got.get("dem_15s"):
        src = next((ext / got["dem_15s"].stem).rglob("*.tif"), None) or next((ext / got["dem_15s"].stem).rglob("*.adf"), None)
        out = sub / "dem_15s_zambia.tif"
        if src and not out.exists():
            with rasterio.open(src) as ds:
                w = from_bounds(*bb, ds.transform).round_offsets().round_lengths()
                arr = ds.read(1, window=w)
                prof = ds.profile.copy()
                for k in ("blockxsize", "blockysize", "tiled"):
                    prof.pop(k, None)
                prof.update(driver="GTiff", width=arr.shape[1], height=arr.shape[0],
                            transform=ds.window_transform(w), compress="deflate")
            with rasterio.open(out, "w", **prof) as dst:
                dst.write(arr, 1)
                dst.update_tags(source=str(src.relative_to(ROOT)), note="window subset, values unchanged",
                                created_utc=utc_now())
            logger.info("DEM subset %s %s nodata=%s", out.name, arr.shape, prof.get("nodata"))
    area = box(*bb)
    for key, name in [("hydrorivers", "hydrorivers_zambia.gpkg"), ("hydrobasins_lev04", "hybas_lev04_zambia.gpkg"),
                      ("hydrobasins_lev06", "hybas_lev06_zambia.gpkg")]:
        out = sub / name
        if got.get(key) is None or out.exists():
            continue
        shp = next((ext / got[key].stem).rglob("*.shp"))
        try:
            g = gpd.read_file(shp, bbox=bb)
        except Exception as e:  # noqa: BLE001 - some HydroBASINS .sbn indexes are unreadable by GDAL
            logger.warning("bbox read failed for %s (%s); reading whole layer and filtering", shp.name, e)
            g = gpd.read_file(shp)
        g = g[g.intersects(area)]
        g.to_file(out, driver="GPKG")
        logger.info("%s: %d features -> %s", key, len(g), out.name)
    if all((sub / n).exists() for n in subset_name.values()) and ext.exists():
        # The unzipped Africa-wide files duplicate the preserved original ZIPs (~600 MB); remove them.
        import shutil
        shutil.rmtree(ext)
        logger.info("Removed temporary extraction folder (originals kept in %s)", orig.relative_to(ROOT))
    if missing:
        sys.exit(1)  # incomplete: re-run resumes the partial downloads


if __name__ == "__main__":
    main()
