"""Collect large-scale climate indices (ENSO and Indian Ocean Dipole) and tidy them to monthly.

Raw (verbatim text files + provenance) in data/raw/climate_indices/:
  oni.ascii.txt                     NOAA CPC Oceanic Nino Index (3-month running mean, ERSST.v5)
  ersst5.nino.mth.91-20.ascii       NOAA CPC monthly Nino regions, anomalies vs 1991-2020
  dmi.had.long.data                 NOAA PSL Dipole Mode Index, monthly (HadISST1.1)
  iod_1.txt                         Australian Bureau of Meteorology weekly IOD index
Tidy (derived, rebuildable): data/processed/climate_indices_monthly.csv, climate_iod_weekly_bom.csv

These are basin-scale indices, NOT local weather. They are kept monthly/weekly and are never
merged onto daily rows here. See docs/DATA_REQUIREMENTS_MATRIX.md for the lag rule.

Usage
  python scripts/download_climate_indices.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, download_file, get_logger, load_config, p  # noqa: E402

SEASON_CENTRE = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8,
                 "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (academic research data collection)"}  # BoM rejects scripted UAs


def parse_oni(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+")
    df["month"] = df["SEAS"].map(SEASON_CENTRE)
    return df.rename(columns={"YR": "year", "TOTAL": "oni_total_c", "ANOM": "oni"})[["year", "month", "oni", "oni_total_c", "SEAS"]] \
             .rename(columns={"SEAS": "oni_season"})


def parse_nino(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+")
    cols = list(df.columns)  # YR MON NINO1+2 ANOM NINO3 ANOM.1 NINO4 ANOM.2 NINO3.4 ANOM.3
    i = cols.index("NINO3.4")
    return pd.DataFrame({"year": df["YR"], "month": df["MON"], "nino34_sst_c": df[cols[i]],
                         "nino34_anom": df[cols[i + 1]]})


def parse_psl(path: Path, name: str) -> pd.DataFrame:
    lines = path.read_text().splitlines()
    y0, y1 = map(int, lines[0].split()[:2])
    rows = []
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) != 13 or not parts[0].isdigit():
            continue
        y = int(parts[0])
        if not y0 <= y <= y1:
            continue
        for m, v in enumerate(parts[1:], start=1):
            rows.append({"year": y, "month": m, name: float(v)})
    df = pd.DataFrame(rows)
    # PSL marks missing with a sentinel given after the data block (e.g. -9999.000)
    miss = [float(ln.split()[0]) for ln in lines if ln.strip().startswith("-99")]
    if miss:
        df.loc[df[name].isin(miss), name] = np.nan
    df.loc[df[name] <= -99, name] = np.nan
    return df


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("climate_indices", cfg)
    ci = cfg["climate_indices"]
    raw = p(cfg, "raw_climate_indices")
    files = {k: download_file(cfg, logger, u, raw / u.rsplit("/", 1)[1], f"climate_indices:{k}",
                              headers=BROWSER_UA if "bom.gov.au" in u else None)
             for k, u in ci.items()}
    out = []
    if files.get("oni"):
        out.append(parse_oni(files["oni"]))
    if files.get("nino34_monthly"):
        out.append(parse_nino(files["nino34_monthly"]))
    if files.get("dmi_monthly_psl"):
        out.append(parse_psl(files["dmi_monthly_psl"], "dmi_hadisst"))
    if out:
        m = out[0]
        for o in out[1:]:
            m = m.merge(o, on=["year", "month"], how="outer")
        m = m.sort_values(["year", "month"])
        m["note"] = "monthly index value for the calendar month; ONI is the 3-month season centred on the month"
        m.to_csv(ROOT / cfg["paths"]["processed"] / "climate_indices_monthly.csv", index=False)
        logger.info("climate_indices_monthly.csv: %d months, %s-%s", len(m), m["year"].min(), m["year"].max())
    if files.get("iod_weekly_bom"):
        w = pd.read_csv(files["iod_weekly_bom"], header=None, names=["week_start", "week_end", "iod_bom"])
        w["week_start"] = pd.to_datetime(w["week_start"].astype(str), format="%Y%m%d")
        w["week_end"] = pd.to_datetime(w["week_end"].astype(str), format="%Y%m%d")
        w.to_csv(ROOT / cfg["paths"]["processed"] / "climate_iod_weekly_bom.csv", index=False)
        logger.info("BoM weekly IOD: %d weeks %s -> %s", len(w), w["week_start"].min().date(), w["week_end"].max().date())


if __name__ == "__main__":
    main()
