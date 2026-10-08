"""Collect independent flood-event evidence for validation (NOT a training label source here).

Dartmouth Flood Observatory (DFO) Global Active Archive of Large Flood Events: event list with
start/end dates, centroid, affected area and main cause, compiled from news, government and
satellite (MODIS) sources. Raw spreadsheet kept verbatim; Zambia rows extracted to
data/processed/dfo_zambia_events.csv for later cross-checking against DesInventar.

Usage
  python scripts/download_flood_observations.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, download_file, get_logger, load_config, p  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("flood_observations", cfg)
    url = cfg["flood_observations"]["dfo_archive"]
    f = download_file(cfg, logger, url, p(cfg, "raw_satellite_flood") / "FloodArchive.xlsx", "dfo_archive",
                      headers={"User-Agent": "Mozilla/5.0 (academic research data collection)"})
    if f is None:
        logger.error("DFO archive not retrieved; re-run when floodobservatory.colorado.edu is reachable")
        sys.exit(1)
    df = pd.read_excel(f)
    text_cols = [c for c in df.columns if df[c].dtype == object]
    mask = df[text_cols].apply(lambda s: s.astype(str).str.contains("Zambia", case=False)).any(axis=1)
    z = df[mask].copy()
    z["source_file"] = str(f.relative_to(ROOT)).replace("\\", "/")
    z.to_csv(ROOT / cfg["paths"]["processed"] / "dfo_zambia_events.csv", index=False)
    dates = pd.to_datetime(df.get("Began"), errors="coerce")
    logger.info("DFO archive: %d events (%s -> %s); Zambia-related: %d", len(df), dates.min(), dates.max(), len(z))


if __name__ == "__main__":
    main()
