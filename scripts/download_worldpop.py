"""Collect WorldPop Zambia population grids (exposure layer, NOT an occurrence predictor).

Product: WorldPop individual-country unconstrained population counts, 30 arc-second (~1 km),
people per pixel, NOT UN-adjusted ("wpic1km"), one GeoTIFF per year. File list comes from the official WorldPop REST API.
Raw: data/raw/worldpop/<file>.tif (+ provenance incl. the API record, DOI and citation).

Usage
  python scripts/download_worldpop.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import download_file, get_logger, get_with_retry, load_config, make_session, p, write_json  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("worldpop", cfg)
    wp = cfg["worldpop"]
    raw = p(cfg, "raw_worldpop")
    meta = get_with_retry(make_session(cfg), wp["api_url"], cfg, logger).json()["data"]
    write_json(raw / "worldpop_api_wpic1km_ZMB.json", meta)
    y0, y1 = wp["years"]
    failed = 0
    for rec in sorted(meta, key=lambda r: int(r["popyear"])):
        if not y0 <= int(rec["popyear"]) <= y1:
            continue
        for url in rec["files"]:
            if url.lower().endswith(".tif"):
                ok = download_file(cfg, logger, url, raw / url.rsplit("/", 1)[1], "worldpop",
                              {"year": rec["popyear"], "title": rec.get("title"), "doi": rec.get("doi"),
                               "citation": rec.get("citation"), "license": rec.get("license"),
                               "api_record_id": rec.get("id")})
                failed += ok is None
    if failed:
        logger.error("WorldPop incomplete: %d files failed (re-run to resume)", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
