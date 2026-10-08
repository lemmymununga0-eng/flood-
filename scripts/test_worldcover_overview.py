"""Computational check: does the WorldCover internal overview reproduce full-resolution class shares?

For several geographically different Zambian windows (~30 x 30 km each), class shares are computed
from the full 10 m tile and from the 1/4 (~40 m) and 1/8 (~80 m) internal overviews of the same
official COG. This tests the *reading method* (overview vs full resolution), NOT the accuracy of
WorldCover itself, and only at the sampled sites.

Output: reports/worldcover_overview_bias_test.csv (one row per site x class x resolution)
Usage
  python scripts/test_worldcover_overview.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p, utc_now  # noqa: E402
from download_worldcover import ENV, tile_name  # noqa: E402

SITES = {  # name: (lat, lon, landscape)
    "Lusaka (urban)": (-15.40, 28.30, "city / peri-urban"),
    "Mongu – Barotse floodplain": (-15.25, 23.10, "floodplain wetland, grassland"),
    "Samfya – Bangweulu": (-11.35, 29.60, "lake shore, swamp"),
    "Kitwe – Copperbelt": (-12.80, 28.20, "mining towns, miombo"),
    "Chipata – Eastern farmland": (-13.60, 32.60, "smallholder cropland"),
    "Kasama – Northern miombo": (-10.20, 31.20, "woodland"),
}
W = 3072  # full-resolution window side in pixels (~30.7 km)


def shares(a: np.ndarray) -> dict:
    v, c = np.unique(a[a != 0], return_counts=True)
    return {int(k): 100 * x / c.sum() for k, x in zip(v, c)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("worldcover_test", cfg)
    classes = {int(k): v for k, v in cfg["worldcover"]["classes"].items()}
    out_path = p(cfg, "reports") / "worldcover_overview_bias_test.csv"
    done = set(pd.read_csv(out_path)["site"]) if out_path.exists() else set()
    rows = []
    for site, (lat, lon, kind) in SITES.items():
        if site in done:
            continue
        lat0, lon0 = math.floor(lat / 3) * 3, math.floor(lon / 3) * 3
        url = "/vsicurl/" + cfg["worldcover"]["tile_url_template"].format(tile=tile_name(lat0, lon0))
        r0 = int((lat0 + 3 - lat) / (3 / 36000)) - W // 2
        c0 = int((lon - lon0) / (3 / 36000)) - W // 2
        r0, c0 = max(0, min(r0, 36000 - W)), max(0, min(c0, 36000 - W))
        try:
            with rasterio.Env(**ENV):
                with rasterio.open(url) as ds:
                    res = {"full_10m": shares(ds.read(1, window=Window(c0, r0, W, W)))}
                for lvl, f in ((1, 4), (2, 8)):
                    with rasterio.open(url, overview_level=lvl) as ds:
                        res[f"overview_1_{f}"] = shares(ds.read(1, window=Window(c0 // f, r0 // f, W // f, W // f)))
        except Exception as e:  # noqa: BLE001
            logger.error("%s failed: %s (re-run to resume)", site, e)
            continue
        for code in sorted(set().union(*[set(d) for d in res.values()])):
            full = res["full_10m"].get(code, 0.0)
            rows.append({"site": site, "landscape": kind, "lat": lat, "lon": lon, "class": classes.get(code, code),
                         "full_10m_pct": round(full, 3),
                         "ov4_pct": round(res["overview_1_4"].get(code, 0.0), 3),
                         "ov8_pct": round(res["overview_1_8"].get(code, 0.0), 3),
                         "ov4_minus_full_pp": round(res["overview_1_4"].get(code, 0.0) - full, 3),
                         "ov8_minus_full_pp": round(res["overview_1_8"].get(code, 0.0) - full, 3),
                         "tested_utc": utc_now()})
        logger.info("%s: max |ov4 - full| = %.2f pp", site,
                    max(abs(r["ov4_minus_full_pp"]) for r in rows if r["site"] == site))
    if rows:
        pd.DataFrame(rows).to_csv(out_path, mode="a", header=not out_path.exists(), index=False)


if __name__ == "__main__":
    main()
