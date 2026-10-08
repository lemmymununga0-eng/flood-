"""Download GloFAS v4.0 time series for the Zambia window from the official Copernicus EWDS.

Products (kept strictly separate — they mean different things):
  historical   cems-glofas-historical  — LISFLOOD forced by ERA5 REANALYSIS ("what happened"). Daily.
               Variables: river discharge (24 h mean), runoff water equivalent (24 h mean),
               soil wetness index (root zone, instantaneous). Use only values <= prediction date t.
  reforecast   cems-glofas-reforecast  — LISFLOOD forced by ECMWF ENS REFORECASTS, initialised twice a
               week; discharge at lead times up to 46 days. This is the archive that supports an honest
               historical FORECAST experiment (information genuinely available at issue time).
  forecast     cems-glofas-forecast    — operational real-time forecasts (from 2019-11; system version
               changes over time). For deployment, not for building the historical training set.

Access: EWDS requires the researcher's own ECMWF account and personal access token in ~/.cdsapirc
(url: https://ewds.climate.copernicus.eu/api, key: <token>) and acceptance of the CEMS-FLOODS licence
on the dataset page. This script never handles credentials; without them it stops with exit code 2.

Valid request combinations (variable names, timespan, product type, reforecast issue dates) are read
from the official public constraints file, so only valid requests are sent.

Raw: data/raw/glofas/<product>/<variable>/<file>.grib2 (+ .provenance.json with the exact request).
Resumable: existing files are skipped. Failures go to reports/failed_requests.csv.

Usage
  python scripts/download_glofas.py --product historical [--years 1999 2026] [--dry-run]
  python scripts/download_glofas.py --product reforecast  [--years 2003 2023] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, record_failure, sha256_file, utc_now, write_json  # noqa: E402

HIST_NAMES = {  # config name -> name used by cems-glofas-historical, with its required timespan
    "river_discharge_in_the_last_24_hours": ("average_river_discharge_in_the_last_24_hours", "time_mean"),
    "runoff_water_equivalent": ("runoff_water_equivalent", "time_mean"),
    "soil_wetness_index": ("soil_wetness_index", "instantaneous"),
}


def constraints(cfg, dataset: str) -> list[dict]:
    cat = requests.get(cfg["glofas"]["catalogue_url"] + dataset, timeout=60).json()
    url = next(l["href"] for l in cat["links"] if l["rel"] == "constraints")
    return requests.get(url, timeout=60).json()


def valid(cons: list[dict], **want) -> bool:
    """True if some constraints row allows every requested key/value."""
    for row in cons:
        if all(any(v == x for x in row.get(k, [])) for k, v in want.items()):
            return True
    return False


def client(cfg, logger):
    rc = Path.home() / ".cdsapirc"
    if not rc.exists():
        logger.error("No EWDS credentials: create an ECMWF account, accept the CEMS-FLOODS licence on the dataset page, "
                     "and put 'url: %s' and 'key: <your token>' in %s. Nothing was downloaded.", cfg["glofas"]["ewds_url"], rc)
        record_failure(cfg, "glofas", "credentials", cfg["glofas"]["ewds_url"], "no ~/.cdsapirc (researcher account required)", 0)
        sys.exit(2)
    import cdsapi
    return cdsapi.Client(url=cfg["glofas"]["ewds_url"], quiet=True)


def historical_jobs(cfg, cons, years):
    h = cfg["glofas"]["historical"]
    months = [f"{m:02d}" for m in range(1, 13)]
    days = [f"{d:02d}" for d in range(1, 32)]
    for var in h["variables"]:
        name, span = HIST_NAMES[var]
        for y in range(years[0], years[1] + 1):
            for ptype in (h["product_type"], "intermediate"):
                ms = [m for m in months if any(valid(cons, system_version=h["system_version"], product_type=ptype, variable=name,
                                                     timespan=span, year=str(y), month=m, day=d) for d in ("01", "15", "28"))]
                if ms:
                    break
            if not ms:
                continue
            req = {"system_version": [h["system_version"]], "hydrological_model": [h["hydrological_model"]],
                   "product_type": [ptype], "variable": [name], "timespan": [span], "year": [str(y)], "month": ms,
                   "day": days, "data_format": h["data_format"], "download_format": "unarchived", "area": cfg["glofas"]["area"]}
            yield h["dataset"], var, f"{var}_{y}_{ptype}.grib2", req


def reforecast_jobs(cfg, cons, years):
    r = cfg["glofas"]["reforecast"]
    for y in range(years[0], years[1] + 1):
        for m in range(1, 13):
            hdays = sorted({d for row in cons if r["system_version"] in row.get("system_version", [])
                            and str(y) in row.get("hyear", []) and f"{m:02d}" in row.get("hmonth", []) for d in row.get("hday", [])})
            if not hdays:
                continue
            for ptype in r["product_type"]:
                req = {"system_version": [r["system_version"]], "hydrological_model": [r["hydrological_model"]],
                       "product_type": [ptype], "variable": r["variables"], "hyear": [str(y)], "hmonth": [f"{m:02d}"],
                       "hday": hdays, "leadtime_hour": [str(x) for x in r["leadtime_hours"]],
                       "data_format": "grib2", "download_format": "unarchived", "area": cfg["glofas"]["area"]}
                yield r["dataset"], "river_discharge_in_the_last_24_hours", f"reforecast_{ptype}_{y}_{m:02d}.grib2", req


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--product", choices=["historical", "reforecast"], required=True)
    ap.add_argument("--years", nargs=2, type=int)
    ap.add_argument("--dry-run", action="store_true", help="validate and list requests without downloading")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("glofas", cfg)
    win = load_window(cfg)
    if args.years:
        years = args.years
    elif args.product == "historical":
        years = (date.fromisoformat(win["start"]).year, date.fromisoformat(win["end"]).year)
    else:
        years = (2003, 2023)
    ds = cfg["glofas"][args.product]["dataset"]
    cons = constraints(cfg, ds)
    jobs = list(historical_jobs(cfg, cons, years) if args.product == "historical" else reforecast_jobs(cfg, cons, years))
    out_root = p(cfg, "raw_glofas") / args.product
    todo = [j for j in jobs if not (out_root / j[1] / j[2]).exists()]
    logger.info("GloFAS %s %s-%s: %d requests valid per official constraints, %d already on disk, %d to fetch",
                args.product, years[0], years[1], len(jobs), len(jobs) - len(todo), len(todo))
    if args.dry_run:
        for ds_, var, fname, req in todo[:3]:
            logger.info("DRY RUN example request %s: %s", fname, json.dumps(req)[:400])
        return
    c = client(cfg, logger)
    failed = 0
    for ds_, var, fname, req in todo:
        out = out_root / var / fname
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_name(out.name + ".part")
        for attempt in range(cfg["http"]["max_retries"]):
            try:
                t0 = time.time()
                c.retrieve(ds_, req, str(part))
                part.replace(out)
                write_json(out.with_name(out.name + ".provenance.json"), {
                    "source": "Copernicus EWDS", "dataset": ds_, "request": req, "retrieved_utc": utc_now(),
                    "bytes": out.stat().st_size, "sha256": sha256_file(out), "seconds": round(time.time() - t0, 1),
                    "licence": "CEMS-FLOODS datasets licence", "doi": {"cems-glofas-historical": "10.24381/cds.a4fdd6b9",
                                                                     "cems-glofas-reforecast": "10.24381/cds.2d78664e"}.get(ds_)})
                logger.info("OK %s (%d bytes)", fname, out.stat().st_size)
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e).lower()
                if any(k in msg for k in ("401", "403", "unauthor", "licence", "license", "not accepted", "invalid key", "forbidden")):
                    logger.error("EWDS refused the request (%s). Check the token in ~/.cdsapirc and that the CEMS-FLOODS "
                                 "licence is accepted on the dataset page. Stopping without retrying.", str(e)[:300])
                    record_failure(cfg, "glofas", fname, cfg["glofas"]["ewds_url"], f"auth/licence: {str(e)[:200]}", attempt + 1)
                    sys.exit(2)
                logger.warning("Attempt %d failed for %s: %s", attempt + 1, fname, e)
                time.sleep(min(cfg["http"]["backoff_max_seconds"], cfg["http"]["backoff_base_seconds"] * 2 ** attempt))
        else:
            failed += 1
            record_failure(cfg, "glofas", fname, cfg["glofas"]["ewds_url"], "retrieve failed after retries", cfg["http"]["max_retries"])
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
