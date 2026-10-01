#!/usr/bin/env python3
"""Run REAL connectivity probes against every catalogued data source and store the
actual outcome. Also corrects descriptions that have gone stale relative to reality
(NASA POWER is reachable from this machine; the event log now holds 14 events).

Nothing is marked "operational" without a real successful probe.

    python scripts/refresh_data_sources.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.integrations.http_health_checker import HttpHealthChecker  # noqa: E402
from app.models.data_source import DataSource  # noqa: E402
from app.services.data_source_health import check_data_source  # noqa: E402

# Description corrections, applied only where the current text is factually wrong.
CORRECTIONS = {
    "NASA POWER": (
        "NASA POWER daily-point API (MERRA-2 reanalysis, not station observation). "
        "Verified reachable and actively used from this machine — it supplies every "
        "weather observation and model input in this deployment."
    ),
    "Hand-compiled Zambia flood-event log": (
        "ai-engine/data/external/zambia_flood_events_log.csv — 14 sourced events "
        "compiled from FloodList/UN-SPIDER/ReliefWeb reporting. Media-derived, not a "
        "primary government dataset."
    ),
}


def main() -> None:
    db = SessionLocal()
    checker = HttpHealthChecker()
    try:
        sources = list(db.scalars(select(DataSource).order_by(DataSource.id)))
        for s in sources:
            for key, text in CORRECTIONS.items():
                if key.lower() in s.name.lower():
                    s.description = text
        db.commit()

        for s in sources:
            updated = check_data_source(db, s, checker)
            print(f"  {updated.name[:48]:50s} {updated.last_check_status:12s} "
                  f"{(updated.last_check_detail or '')[:70]}")
        db.commit()
        print(f"\nProbed {len(sources)} sources with real HTTP requests.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
