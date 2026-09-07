"""Real connectivity checks for the data-source catalog. Mirrors the honesty rule in
app/services/weather_ingestion.py: on failure, the actual exception is stored, never a
fabricated "operational" status. A failure here (this sandbox's egress policy blocks
NASA POWER and DMMU's site has a redirect-loop issue — see docs/DATA-SOURCES.md) is
expected in this environment and is not silently hidden."""
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from app.models.data_source import DataSource


def check_data_source(db: Session, source: DataSource, timeout_s: float = 8.0) -> DataSource:
    if not source.base_url:
        source.last_check_status = "unknown"
        source.last_check_detail = "No base_url configured for this source."
        source.last_checked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(source)
        return source

    try:
        resp = requests.head(source.base_url, timeout=timeout_s, allow_redirects=True)
        if resp.status_code >= 400:
            # Some hosts (e.g. NASA POWER's base domain) reject HEAD; retry with GET
            # before concluding failure.
            resp = requests.get(source.base_url, timeout=timeout_s, allow_redirects=True)
        source.last_check_status = "ok" if resp.status_code < 400 else "failed"
        source.last_check_detail = f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        source.last_check_status = "failed"
        source.last_check_detail = f"{type(exc).__name__}: {exc}"

    source.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)
    return source
