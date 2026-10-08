"""Download NASA POWER daily point data for every location in the location master.

One API request returns a multi-decade daily series for one point, so the pipeline makes
one request per location per *missing* period (never re-requests what is cached).

Raw store (never modified after writing):
  data/raw/nasa_power/daily_weather/<location_id>/<location_id>__<start>_<end>.json   API response verbatim
  data/raw/nasa_power/daily_weather/<location_id>/<location_id>__<start>_<end>.meta.json
Tabular extraction (rebuildable from the raw JSON at any time):
  data/raw/nasa_power/nasa_power_daily.csv   long table, -999 fill values written as empty (missing)
Manifest / failures:
  data/raw/nasa_power/download_manifest.csv  one row per request attempted in this run
  reports/failed_requests.csv                appended on failure

Usage
  python scripts/download_nasa_power.py                     # all locations, window from collection_window.json
  python scripts/download_nasa_power.py --limit 3           # first 3 locations only (smoke test)
  python scripts/download_nasa_power.py --start 2000-01-01 --end 2000-12-31
  python scripts/download_nasa_power.py --rebuild-only      # only rebuild the CSV from cached JSON
  python scripts/download_nasa_power.py --dataset soil      # optional soil-wetness experiment (GWETTOP/ROOT/PROF)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ROOT, get_logger, get_with_retry, load_config, load_window, make_session, p,  # noqa: E402
                     record_failure, sha256_file, utc_now, write_json)


def cached_ranges(loc_dir: Path, loc_id: str) -> list[tuple[date, date]]:
    out = []
    for f in loc_dir.glob(f"{loc_id}__*.json"):
        if f.name.endswith(".meta.json"):
            continue
        a, b = f.stem.split("__")[1].split("_")
        out.append((date.fromisoformat(a), date.fromisoformat(b)))
    return sorted(out)


def missing_periods(want_start: date, want_end: date, have: list[tuple[date, date]]) -> list[tuple[date, date]]:
    gaps, cur = [], want_start
    for a, b in have:
        if b < cur or a > want_end:
            continue
        if a > cur:
            gaps.append((cur, min(want_end, a - timedelta(days=1))))
        cur = max(cur, b + timedelta(days=1))
    if cur <= want_end:
        gaps.append((cur, want_end))
    return gaps


def split(a: date, b: date, years: int) -> list[tuple[date, date]]:
    out = []
    while a <= b:
        e = min(b, date(a.year + years, a.month, a.day) - timedelta(days=1))
        out.append((a, e))
        a = e + timedelta(days=1)
    return out


def fetch(loc, a: date, b: date, cfg, logger, session) -> dict:
    n = cfg["nasa_power"]
    params = {"parameters": ",".join(n["parameters"]), "community": n["community"],
              "longitude": loc.longitude, "latitude": loc.latitude,
              "start": a.strftime("%Y%m%d"), "end": b.strftime("%Y%m%d"),
              "format": "JSON", "time-standard": n["time_standard"]}
    loc_dir = p(cfg, "raw_nasa_power") / loc.location_id
    loc_dir.mkdir(exist_ok=True)
    stem = f"{loc.location_id}__{a.isoformat()}_{b.isoformat()}"
    url = n["api_url"]
    t0 = time.time()
    try:
        r = get_with_retry(session, url, cfg, logger, params=params)
        payload = r.json()
        got = payload["properties"]["parameter"]
        missing = [v for v in n["parameters"] if v not in got]
        if missing:
            raise ValueError(f"response lacks parameters {missing}; messages={payload.get('messages')}")
    except Exception as e:  # noqa: BLE001
        full = f"{url}?" + "&".join(f"{k}={v}" for k, v in params.items())
        record_failure(cfg, n.get("source_tag", "nasa_power"), stem, full, repr(e), getattr(e, "attempts", 1))
        logger.error("FAILED %s: %s", stem, e)
        return {"location_id": loc.location_id, "start": a, "end": b, "status": "failed", "error": repr(e)[:300]}
    raw_path = loc_dir / f"{stem}.json"
    tmp = raw_path.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(raw_path)
    write_json(loc_dir / f"{stem}.meta.json", {
        "location_id": loc.location_id, "latitude_requested": loc.latitude, "longitude_requested": loc.longitude,
        "request_url": r.url, "params": params, "http_status": r.status_code, "retrieved_utc": utc_now(),
        "elapsed_seconds": round(time.time() - t0, 2), "bytes": raw_path.stat().st_size,
        "sha256": sha256_file(raw_path), "api_header": payload.get("header"),
        "api_messages": payload.get("messages"), "parameter_metadata": payload.get("parameters"),
    })
    logger.info("OK %s (%d bytes, %.1fs)", stem, raw_path.stat().st_size, time.time() - t0)
    return {"location_id": loc.location_id, "start": a, "end": b, "status": "downloaded", "error": ""}


def rebuild_csv(cfg, logger, master: pd.DataFrame) -> Path:
    """Flatten every cached raw JSON into one long CSV. Fill value -> missing; nothing else changes."""
    n = cfg["nasa_power"]
    fill = n["fill_value"]
    root = p(cfg, "raw_nasa_power")
    coords = master.set_index("location_id")[["latitude", "longitude"]]
    frames = []
    for f in sorted(root.glob("*/*.json")):
        if f.name.endswith(".meta.json"):
            continue
        meta = json.loads(f.with_name(f.stem + ".meta.json").read_text(encoding="utf-8"))
        payload = json.loads(f.read_text(encoding="utf-8"))
        par = payload["properties"]["parameter"]
        df = pd.DataFrame({v: pd.Series(par[v]) for v in n["parameters"]})
        df.index.name = "yyyymmdd"
        df = df.reset_index()
        df.insert(0, "date", pd.to_datetime(df.pop("yyyymmdd"), format="%Y%m%d").dt.strftime("%Y-%m-%d"))
        for v in n["parameters"]:
            df[v] = df[v].where(df[v] != fill)  # NASA POWER fill value -999 = missing
        loc = meta["location_id"]
        df.insert(0, "longitude", coords.loc[loc, "longitude"])
        df.insert(0, "latitude", coords.loc[loc, "latitude"])
        df.insert(0, "location_id", loc)
        geom = payload.get("geometry", {}).get("coordinates", [None, None])
        df["power_point_longitude"], df["power_point_latitude"] = geom[0], geom[1]
        df["source"] = "NASA POWER Daily API " + str((meta.get("api_header") or {}).get("api", {}).get("version", ""))
        df["community"] = meta["params"]["community"]
        df["time_standard"] = meta["params"].get("time-standard", n["time_standard"])
        df["retrieval_timestamp_utc"] = meta["retrieved_utc"]
        df["raw_file"] = str(f.relative_to(ROOT)).replace("\\", "/")
        frames.append(df)
    if not frames:
        raise SystemExit("No cached NASA POWER responses to flatten")
    out = pd.concat(frames, ignore_index=True)
    # Overlapping cached chunks (e.g. after a window change) must not produce duplicate rows:
    # keep the most recently retrieved value for each (location, date).
    before = len(out)
    out = (out.sort_values(["location_id", "date", "retrieval_timestamp_utc"])
              .drop_duplicates(["location_id", "date"], keep="last"))
    if before != len(out):
        logger.info("Dropped %d overlapping rows from repeated chunks (kept latest retrieval)", before - len(out))
    path = root.parent / n.get("csv_name", "nasa_power_daily.csv")
    out.to_csv(path, index=False)
    logger.info("Wrote %s: %d rows, %d locations, %s -> %s", path.relative_to(ROOT), len(out),
                out["location_id"].nunique(), out["date"].min(), out["date"].max())
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--start", help="override window start YYYY-MM-DD")
    ap.add_argument("--end", help="override window end YYYY-MM-DD")
    ap.add_argument("--limit", type=int, help="only the first N locations")
    ap.add_argument("--rebuild-only", action="store_true", help="skip downloading; rebuild the CSV")
    ap.add_argument("--dataset", choices=["weather", "soil"], default="weather",
                    help="weather = core variables; soil = optional soil-wetness experiment (nasa_power_soil)")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("nasa_power", cfg)
    if args.dataset == "soil":
        soil = cfg["nasa_power_soil"]
        cfg["nasa_power"] = {**cfg["nasa_power"], "parameters": soil["parameters"], "community": soil["community"],
                             "csv_name": "nasa_power_daily_soil_moisture.csv", "source_tag": "nasa_power_soil"}
        cfg["paths"]["raw_nasa_power"] = cfg["paths"]["raw_nasa_power_soil"]
    n = cfg["nasa_power"]

    master = pd.read_csv(ROOT / cfg["paths"]["processed"] / "location_master.csv")
    locs = master[master["in_weather_collection"]]
    if args.limit:
        locs = locs.head(args.limit)
    win = load_window(cfg)
    start = date.fromisoformat(args.start or win["start"])
    end = min(date.fromisoformat(args.end or win["end"]), date.today() - timedelta(days=1))

    if not args.rebuild_only:
        root = p(cfg, "raw_nasa_power")
        jobs = []
        for loc in locs.itertuples():
            gaps = missing_periods(start, end, cached_ranges(root / loc.location_id, loc.location_id))
            for a, b in gaps:
                jobs.extend((loc, x, y) for x, y in split(a, b, n["max_years_per_request"]))
        cached = len(locs) - len({j[0].location_id for j in jobs})
        logger.info("NASA POWER %s -> %s: %d locations, %d fully cached, %d requests needed",
                    start, end, len(locs), cached, len(jobs))
        session = make_session(cfg)
        results = []
        with ThreadPoolExecutor(max_workers=n["max_workers"]) as ex:
            futs = []
            for i, (loc, a, b) in enumerate(jobs):
                futs.append(ex.submit(fetch, loc, a, b, cfg, logger, session))
                if n["max_workers"] == 1:
                    futs[-1].result()
                    if i < len(jobs) - 1:
                        time.sleep(n["pause_seconds"])
            for f in as_completed(futs):
                results.append(f.result())
        if results:
            man = pd.DataFrame(results).assign(run_utc=utc_now())
            mpath = root.parent / "download_manifest.csv"
            man.to_csv(mpath, mode="a", header=not mpath.exists(), index=False)
            logger.info("Requests: %s", man["status"].value_counts().to_dict())
            if (man["status"] == "failed").any():
                rebuild_csv(cfg, logger, master)
                sys.exit(1)  # incomplete: callers/loops re-run to fetch only what is missing
    rebuild_csv(cfg, logger, master)


if __name__ == "__main__":
    main()
