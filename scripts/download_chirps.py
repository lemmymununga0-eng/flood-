"""Collect CHIRPS v3.0 daily rainfall for the Zambia window, independently of NASA POWER.

Efficiency: CHIRPS publishes each day as a global Cloud-Optimised GeoTIFF (COG). Only the tiles
covering the Zambia bounding box are fetched with HTTP range requests (~4 tiles/day) instead of
the 17 MB global GeoTIFF or the 3.6 GB yearly global NetCDF. Pixel values are copied unchanged.

Raw store
  data/raw/chirps/daily_rainfall/_daily/<YYYY>/chirps-v3.0.<variant>.<YYYY.MM.DD>.zambia.tif   per-day clip (resume cache)
  data/raw/chirps/daily_rainfall/chirps-v3.0.<variant>.zambia.<YYYY>.nc   one file per year, built once every day
                                                                          of that year in the window is present;
                                                                          the per-day clips are then removed
  data/raw/chirps/chirps_manifest.csv     one row per day: source URL, status, retrieval time, value summary
Derived (rebuildable): data/processed/chirps_daily_at_locations.csv   nearest-pixel series at each location
Failures: reports/failed_requests.csv

Usage
  python scripts/download_chirps.py                         # window from collection_window.json
  python scripts/download_chirps.py --start 2020-01-01 --end 2020-01-31
  python scripts/download_chirps.py --workers 4
  python scripts/download_chirps.py --extract-only          # only rebuild the point extraction
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, record_failure, utc_now  # noqa: E402

GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".cog,.tif",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE",
                # Hard limits so a stalled connection is aborted (and retried) instead of hanging a worker.
                GDAL_HTTP_CONNECTTIMEOUT="30", GDAL_HTTP_LOW_SPEED_TIME="60", GDAL_HTTP_LOW_SPEED_LIMIT="1")


def day_paths(cfg, d: date) -> tuple[str, Path]:
    c = cfg["chirps"]
    url = c["cog_url_template"].format(stream=c["stream"], variant=c["variant"], year=d.year, month=d.month, day=d.day)
    out = p(cfg, "raw_chirps") / "_daily" / f"{d.year}" / f"chirps-v3.0.{c['variant']}.{d:%Y.%m.%d}.zambia.tif"
    return url, out


def year_nc(cfg, year: int) -> Path:
    return p(cfg, "raw_chirps") / f"chirps-v3.0.{cfg['chirps']['variant']}.zambia.{year}.nc"


def fetch_day(d: date, cfg, logger) -> dict:
    c = cfg["chirps"]
    b = c["bbox"]
    url, out = day_paths(cfg, d)
    h = cfg["http"]
    last = None
    for attempt in range(h["max_retries"]):
        try:
            with rasterio.Env(**GDAL_ENV, GDAL_HTTP_TIMEOUT=str(h["timeout_seconds"]),
                              GDAL_HTTP_USERAGENT=h["user_agent"]):
                with rasterio.open("/vsicurl/" + url) as ds:
                    w = from_bounds(b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"], ds.transform)
                    w = w.round_offsets().round_lengths()
                    arr = ds.read(1, window=w)
                    prof = ds.profile.copy()
                    for k in ("blockxsize", "blockysize", "tiled", "interleave"):
                        prof.pop(k, None)
                    prof.update(width=arr.shape[1], height=arr.shape[0], transform=ds.window_transform(w),
                                compress="lzw", predictor=3)
                    tags = ds.tags()
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_suffix(".part.tif")
            with rasterio.open(tmp, "w", **prof) as dst:
                dst.write(arr, 1)
                dst.update_tags(source_url=url, retrieved_utc=utc_now(), **{f"src_{k}": v for k, v in tags.items()})
            tmp.replace(out)
            nod = np.isin(arr, c["nodata_values"]) | ~np.isfinite(arr)
            valid = arr[~nod]
            return {"date": d.isoformat(), "url": url, "status": "ok", "retrieved_utc": utc_now(),
                    "n_pixels": arr.size, "n_nodata": int(nod.sum()), "n_negative": int((valid < 0).sum()),
                    "min": float(valid.min()) if valid.size else np.nan,
                    "max": float(valid.max()) if valid.size else np.nan,
                    "mean": float(valid.mean()) if valid.size else np.nan, "error": ""}
        except rasterio.errors.RasterioIOError as e:
            last = e
            if "404" in str(e) or "does not exist" in str(e) or "No such file" in str(e):
                break  # not published: retrying will not help
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(min(h["backoff_max_seconds"], h["backoff_base_seconds"] * 2 ** attempt))
    status = "not_available" if last and ("404" in str(last) or "does not exist" in str(last)) else "failed"
    record_failure(cfg, "chirps", d.isoformat(), url, f"{status}: {last!r}", attempt + 1)
    logger.error("CHIRPS %s %s: %s", d, status, last)
    return {"date": d.isoformat(), "url": url, "status": status, "retrieved_utc": utc_now(), "error": repr(last)[:300]}


def consolidate_year(cfg, logger, year: int, days: list[date]) -> bool:
    """Stack a year's per-day clips into one NetCDF (values unchanged), verify, remove the clips."""
    files = [day_paths(cfg, d)[1] for d in days]
    out = year_nc(cfg, year)
    old = xr.load_dataset(out) if out.exists() else None  # days already consolidated earlier
    held = set(pd.to_datetime(old["time"].values).date) if old is not None else set()
    if not all(f.exists() or d in held for f, d in zip(files, days)):
        return False
    arrays, urls, times, lat, lon = [], [], [], None, None
    for f, d in zip(files, days):
        if f.exists():
            with rasterio.open(f) as ds:
                arrays.append(ds.read(1))
                tr, shape = ds.transform, ds.shape
                urls.append(ds.tags().get("source_url", ""))
                times.append(ds.tags().get("retrieved_utc", ""))
            lon = tr.c + tr.a * (np.arange(shape[1]) + 0.5)
            lat = tr.f + tr.e * (np.arange(shape[0]) + 0.5)
        else:
            row = old.sel(time=pd.Timestamp(d))
            arrays.append(row["precip"].values)
            urls.append(str(row["source_url"].values))
            times.append(str(row["retrieved_utc"].values))
    if lat is None:
        lat, lon = old["lat"].values, old["lon"].values
    c = cfg["chirps"]
    da = xr.DataArray(np.stack(arrays), dims=("time", "lat", "lon"),
                      coords={"time": pd.to_datetime(days), "lat": lat, "lon": lon}, name="precip")
    da.attrs = {"units": "mm/day", "long_name": "CHIRPS v3.0 daily precipitation",
                "note": "pixel values copied unchanged from the CHC global daily COGs"}
    ds = da.to_dataset()
    ds["source_url"] = ("time", np.array(urls, dtype=object))
    ds["retrieved_utc"] = ("time", np.array(times, dtype=object))
    ds.attrs = {"title": f"CHIRPS v3.0 daily ({c['variant']}, {c['stream']}) — Zambia window {year}",
                "source": c["home_url"], "data_root": c["data_root"], "variant": c["variant"],
                "bbox": str(c["bbox"]), "resolution_deg": 0.05, "created_utc": utc_now(),
                "citation": "Funk et al. (2015) Sci Data 2:150066; CHIRPS v3.0, Climate Hazards Center, UCSB"}
    tmp = out.with_suffix(".part.nc")
    ds.to_netcdf(tmp, encoding={"precip": {"zlib": True, "complevel": 4, "shuffle": True, "dtype": "float32"}})
    with xr.open_dataset(tmp) as chk:  # verify lossless before deleting the clips
        ok = chk.sizes["time"] == len(days) and np.array_equal(chk["precip"].values, da.values, equal_nan=True)
    if not ok:
        logger.error("Verification failed for %s; keeping per-day clips", tmp.name)
        tmp.unlink()
        return False
    tmp.replace(out)
    for f in files:
        f.unlink(missing_ok=True)
    logger.info("Consolidated %d days -> %s", len(days), out.relative_to(ROOT))
    return True


def extract_points(cfg, logger):
    master = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv")
    master = master[master["in_weather_collection"]]
    frames = []
    for nc in sorted(f for f in p(cfg, "raw_chirps").glob("*.zambia.*.nc") if ".part" not in f.name):
        with xr.open_dataset(nc) as ds:
            sel = ds["precip"].sel(lat=xr.DataArray(master["latitude"].values, dims="loc"),
                                   lon=xr.DataArray(master["longitude"].values, dims="loc"), method="nearest")
            df = pd.DataFrame(sel.values.T, index=master["location_id"].values,
                              columns=pd.to_datetime(ds["time"].values).strftime("%Y-%m-%d"))
            df = df.stack(future_stack=True).rename("chirps_precip_mm").reset_index()
            df.columns = ["location_id", "date", "chirps_precip_mm"]
            px = pd.DataFrame({"location_id": master["location_id"].values,
                               "pixel_lat": np.round(sel["lat"].values, 4), "pixel_lon": np.round(sel["lon"].values, 4)})
            df = df.merge(px, on="location_id")
            df["source_file"] = str(nc.relative_to(ROOT)).replace("\\", "/")
            frames.append(df)
    if not frames:
        logger.warning("No CHIRPS yearly files to extract from")
        return
    out = pd.concat(frames, ignore_index=True).sort_values(["location_id", "date"])
    nod = out["chirps_precip_mm"].isin(cfg["chirps"]["nodata_values"])
    out.loc[nod, "chirps_precip_mm"] = np.nan  # documented nodata code -> missing
    path = ROOT / cfg["paths"]["processed"] / "chirps_daily_at_locations.csv"
    out.to_csv(path, index=False)
    logger.info("Wrote %s: %d rows, %d locations", path.relative_to(ROOT), len(out), out["location_id"].nunique())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--extract-only", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("chirps", cfg)
    c = cfg["chirps"]
    if not args.extract_only:
        win = load_window(cfg)
        start = date.fromisoformat(args.start or win["start"])
        end = date.fromisoformat(args.end or win["end"])
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        by_year: dict[int, list[date]] = {}
        for d in days:
            by_year.setdefault(d.year, []).append(d)
        todo = []
        for y, ds in by_year.items():
            nc = year_nc(cfg, y)
            if nc.exists():
                with xr.open_dataset(nc) as chk:
                    have = set(pd.to_datetime(chk["time"].values).date)
                if set(ds) <= have:
                    continue
                logger.info("%s lacks some requested days; only those are fetched, then the year is rebuilt", nc.name)
                by_year[y] = sorted(have | set(ds))
            else:
                have = set()
            todo.extend(d for d in ds if d not in have and not day_paths(cfg, d)[1].exists())
        todo = sorted(set(todo))
        logger.info("CHIRPS %s %s -> %s: %d days, %d to fetch, %d years", c["variant"], start, end,
                    len(days), len(todo), len(by_year))
        mpath = p(cfg, "raw_chirps").parent / "chirps_manifest.csv"
        workers = args.workers or c["max_workers"]
        done, t0 = 0, time.time()
        # Year by year, consolidating as soon as a year is complete, so at most ~365 per-day clips
        # exist on disk at any time and an interruption loses at most one year's partial work.
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for y, ds in sorted(by_year.items()):
                year_todo = [d for d in todo if d.year == y]
                buf = [f.result() for f in as_completed([ex.submit(fetch_day, d, cfg, logger) for d in year_todo])]
                if buf:
                    pd.DataFrame(buf).sort_values("date").to_csv(mpath, mode="a", header=not mpath.exists(), index=False)
                # Circuit breaker: if a whole batch failed on connectivity, stop instead of logging
                # thousands of identical failures. Re-running later resumes from here.
                failed = [r for r in buf if r["status"] == "failed"]
                if len(buf) >= 20 and len(failed) > 0.5 * len(buf):
                    logger.error("Stopping: %d/%d days of %d failed (network or server down?). "
                                 "Re-run the script later to resume.", len(failed), len(buf), y)
                    break
                done += len(year_todo)
                if any(day_paths(cfg, d)[1].exists() for d in ds) or not year_nc(cfg, y).exists():
                    if not consolidate_year(cfg, logger, y, ds):
                        logger.warning("Year %d incomplete; per-day clips kept for the next run", y)
                rate = done / (time.time() - t0) if done else 0
                logger.info("CHIRPS progress %d/%d days (year %d done; %.2f days/s, ~%.0f min left)", done,
                            len(todo), y, rate, (len(todo) - done) / rate / 60 if rate else 0)
    if c.get("extract_points", True):
        extract_points(cfg, logger)


if __name__ == "__main__":
    main()
