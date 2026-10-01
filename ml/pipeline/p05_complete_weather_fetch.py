"""Complete the interrupted 11-parameter NASA POWER fetch.

The research bundle's `nasa_power_zambia_flood_locations.csv` covers only 59 of the 82
locations, and a few of those partially: the fetch aborted on a DNS resolution failure
(see refetch_11param.log). Training on 59 locations would be an undocumented reduction in
spatial coverage, so this script fills the gaps rather than letting the pipeline quietly
shrink.

It is additive and idempotent:
  * reads the existing export, works out exactly which (location, decade) chunks are
    missing or short, and requests only those;
  * caches every raw JSON response so a re-run costs nothing;
  * writes a NEW complete file under OUT_ROOT and never modifies the baseline export.

NASA POWER's -999 sentinel is converted to null, never stored as a reading.

    python ml/pipeline/p05_complete_weather_fetch.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import requests  # noqa: E402

from ml import config as C  # noqa: E402

PARAMETERS = ("PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS10M,"
              "GWETROOT,GWETPROF,GWETTOP,T2MDEW,PS")
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL = -999.0
CHUNKS = [("19900101", "19991231"), ("20000101", "20091231"),
          ("20100101", "20191231"), ("20200101", "20260915")]
CACHE = C.OUT_ROOT / "nasa_power_cache"
OUT = C.PROCESSED_DIR / "weather_complete.csv"


def fetch_chunk(name: str, lat: float, lon: float, start: str, end: str,
                *, retries: int = 4) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"{name.replace(' ', '_').replace(chr(39), '')}_{start}_{end}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache_file.unlink()

    params = {"parameters": PARAMETERS, "community": "AG", "longitude": lon,
              "latitude": lat, "start": start, "end": end, "format": "JSON"}
    for attempt in range(retries):
        try:
            r = requests.get(BASE_URL, params=params, timeout=90)
            r.raise_for_status()
            payload = r.json()
            if "properties" not in payload:
                raise ValueError("unexpected response shape")
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
            return payload
        except Exception as exc:  # noqa: BLE001 - transient network is expected here
            wait = 2 ** attempt * 3
            print(f"      attempt {attempt + 1}/{retries} failed ({type(exc).__name__}); "
                  f"retry in {wait}s", flush=True)
            time.sleep(wait)
    print(f"      GIVING UP on {name} {start}-{end} - reported, not faked", flush=True)
    return None


def to_frame(name: str, payload: dict) -> pd.DataFrame:
    block = payload["properties"]["parameter"]
    dates = sorted(block.get("PRECTOTCORR", {}).keys())
    rows = {"location": [name] * len(dates),
            "date": pd.to_datetime(dates, format="%Y%m%d")}
    for p in PARAMETERS.split(","):
        vals = block.get(p, {})
        rows[p] = [None if vals.get(d) in (None, FILL) else vals.get(d) for d in dates]
    return pd.DataFrame(rows)


def main() -> None:
    C.ensure_out_dirs()
    locs = pd.read_csv(C.LOCATIONS_CSV)
    existing = pd.read_csv(C.WEATHER_CSV, parse_dates=["date"], low_memory=False)

    expected_days = len(pd.date_range("1990-01-01", "2026-09-15"))
    counts = existing.groupby("location").size()
    complete = set(counts[counts >= expected_days - 60].index)
    print(f"existing export: {existing.location.nunique()} locations, "
          f"{len(complete)} of them complete")

    frames = [existing[existing.location.isin(complete)]]
    todo = [r for r in locs.itertuples() if r.name not in complete]
    print(f"fetching {len(todo)} location(s) x {len(CHUNKS)} chunks")

    failed: list[str] = []
    for i, r in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {r.name}", flush=True)
        parts = []
        for start, end in CHUNKS:
            payload = fetch_chunk(r.name, r.lat, r.lon, start, end)
            if payload is None:
                failed.append(f"{r.name} {start}-{end}")
                continue
            parts.append(to_frame(r.name, payload))
        if parts:
            frames.append(pd.concat(parts, ignore_index=True))

    out = (pd.concat(frames, ignore_index=True)
           .drop_duplicates(subset=["location", "date"], keep="first")
           .sort_values(["location", "date"])
           .reset_index(drop=True))
    out.to_csv(OUT, index=False)

    print(f"\nWrote {OUT}")
    print(f"  locations={out.location.nunique()} rows={len(out):,} "
          f"{out.date.min().date()} -> {out.date.max().date()}")
    missing = sorted(set(locs.name) - set(out.location))
    if missing:
        print(f"  STILL MISSING ({len(missing)}): {missing}")
    if failed:
        print(f"  failed chunks ({len(failed)}): {failed[:10]}")


if __name__ == "__main__":
    main()
