"""Shared helpers for the Stage 1 raw-data scripts: config, logging, HTTP with retry, failure log."""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import random
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "data_sources.yaml"

_failure_lock = threading.Lock()


def load_config(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def p(cfg: dict, key: str) -> Path:
    """Resolve a configured path relative to the project root and make sure it exists."""
    path = ROOT / cfg["paths"][key]
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logger(name: str, cfg: dict) -> logging.Logger:
    log_cfg = cfg["logging"]
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(log_cfg.get("level", "INFO"))
    fmt = logging.Formatter(log_cfg["format"])
    log_file = ROOT / log_cfg["file"]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, default=str)
    tmp.replace(path)


def record_failure(cfg: dict, source: str, target: str, url: str, error: str, attempts: int) -> None:
    """Append one failed request to reports/failed_requests.csv (shared by all downloaders)."""
    path = ROOT / cfg["paths"]["reports"] / "failed_requests.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with _failure_lock:
        new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["timestamp_utc", "source", "target", "url", "attempts", "error"])
            w.writerow([utc_now(), source, target, url, attempts, error[:500]])


def make_session(cfg: dict) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = cfg["http"]["user_agent"]
    return s


def get_with_retry(session: requests.Session, url: str, cfg: dict, logger: logging.Logger,
                   params: dict | None = None, stream: bool = False) -> requests.Response:
    """GET with exponential backoff on network errors and retryable HTTP codes.

    Non-retryable HTTP errors (e.g. 404) raise immediately. Raises the last error after
    max_retries; callers record the failure and carry on with the next item.
    """
    h = cfg["http"]
    last: Exception | None = None
    for attempt in range(h["max_retries"]):
        try:
            r = session.get(url, params=params, timeout=h["timeout_seconds"], stream=stream)
            if r.status_code in h["retry_status_codes"]:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code is not None and code not in h["retry_status_codes"]:
                e.attempts = attempt + 1
                raise
            last = e
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
        wait = min(h["backoff_max_seconds"], h["backoff_base_seconds"] * 2 ** attempt) + random.uniform(0, 1)
        logger.warning("Attempt %d/%d failed for %s (%s); retrying in %.1fs",
                       attempt + 1, h["max_retries"], url, last, wait)
        time.sleep(wait)
    last.attempts = h["max_retries"]  # type: ignore[union-attr]
    raise last  # type: ignore[misc]


def download_file(cfg: dict, logger: logging.Logger, url: str, dest: Path, source: str,
                  extra_provenance: dict | None = None, headers: dict | None = None) -> Path | None:
    """Resumable download of one file, written once and never overwritten.

    Skips if dest and its .provenance.json already exist. Interrupted downloads resume from the
    .part file with an HTTP Range request. Writes dest.provenance.json (URL, time, size, sha256).
    Returns None (and logs to failed_requests.csv) if all retries fail.
    """
    dest = Path(dest)
    prov = dest.with_name(dest.name + ".provenance.json")
    if dest.exists() and prov.exists():
        logger.info("Cached, not downloading again: %s", dest.relative_to(ROOT))
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    h = cfg["http"]
    session = make_session(cfg)
    if headers:
        session.headers.update(headers)
    last = None
    for attempt in range(h["max_retries"] * 2):
        have = part.stat().st_size if part.exists() else 0
        try:
            r = session.get(url, stream=True, timeout=h["timeout_seconds"],
                            headers={"Range": f"bytes={have}-"} if have else {})
            if r.status_code == 416:  # already complete
                break
            if r.status_code not in (200, 206):
                if r.status_code not in h["retry_status_codes"]:
                    record_failure(cfg, source, dest.name, url, f"HTTP {r.status_code}", attempt + 1)
                    logger.error("HTTP %s for %s", r.status_code, url)
                    return None
                raise requests.HTTPError(f"HTTP {r.status_code}")
            mode = "ab" if (have and r.status_code == 206) else "wb"
            with open(part, mode) as fh:
                for chunk in r.iter_content(1 << 16):
                    fh.write(chunk)
            total = r.headers.get("Content-Range", "").split("/")[-1] if r.status_code == 206 else r.headers.get("Content-Length")
            if total and total.isdigit() and part.stat().st_size < int(total):
                raise requests.ConnectionError(f"short read {part.stat().st_size}/{total}")
            last_headers = dict(r.headers)
            break
        except (requests.RequestException, OSError) as e:
            last = e
            wait = min(h["backoff_max_seconds"], h["backoff_base_seconds"] * 2 ** min(attempt, 6)) + random.uniform(0, 1)
            logger.warning("Download attempt %d failed for %s (%s); resuming in %.0fs", attempt + 1, url, e, wait)
            time.sleep(wait)
    else:
        record_failure(cfg, source, dest.name, url, repr(last), h["max_retries"] * 2)
        logger.error("FAILED download %s: %s", url, last)
        return None
    part.replace(dest)
    write_json(prov, {"source": source, "url": url, "retrieved_utc": utc_now(), "bytes": dest.stat().st_size,
                      "sha256": sha256_file(dest), "last_modified": locals().get("last_headers", {}).get("Last-Modified"),
                      **(extra_provenance or {})})
    logger.info("Downloaded %s (%d bytes)", dest.relative_to(ROOT), dest.stat().st_size)
    return dest


def load_window(cfg: dict) -> dict:
    """The collection window written by collect_desinventar.py (or explicit config dates)."""
    w = cfg["collection_window"]
    path = ROOT / cfg["paths"]["processed"] / "collection_window.json"
    derived = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    start = derived.get("start") if w["start"] == "auto" else str(w["start"])
    end = derived.get("end") if w["end"] == "auto" else str(w["end"])
    if not start or not end:
        raise SystemExit("Collection window unknown: run scripts/collect_desinventar.py first "
                         "or set collection_window.start/end in config/data_sources.yaml")
    return {"start": start, "end": end}
