"""Seed the database with REAL data only:
- Locations: Lusaka (city-level) plus Kanyama and Ng'ombe, the two settlements this
  project independently verified as flood-affected via peer-reviewed/graduate research
  (see docs/PROJECT-MEMORY.md, 2026-09-07 geographic-scope entry). Coordinates are
  city-approximate, not surveyed — coordinate_confidence reflects that.
- Flood events: the 11 rows in ai-engine/data/external/zambia_flood_events_log.csv,
  loaded verbatim with their source citations.
- Roles: the five fixed roles (ADMIN/ANALYST/OPERATOR/RESEARCHER/CITIZEN) the RBAC
  system checks against — these are not arbitrary, the API rejects any role name
  outside this set implicitly (no role-creation endpoint exists).
- One local-development ADMIN account, ONLY if FLOODSHIELD_DEV_ADMIN_PASSWORD is set
  in the environment — never a hardcoded default password. If unset, no admin account
  is created and this is reported, not silently skipped.
- Data sources: the real catalog of external sources this project depends on, with a
  live connectivity status set by an actual check, not asserted.

Nothing here is synthetic. No WeatherObservation, ModelVersion, or Prediction rows are
seeded — those only get populated by a real ingestion run or a real trained model.
Safe to re-run: it upserts by unique key rather than duplicating rows.

This script assumes migrations have already been applied (`alembic upgrade head`) — it
no longer calls Base.metadata.create_all(); schema is Alembic's responsibility now.
"""
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.models.data_source import DataSource  # noqa: E402
from app.models.flood_event import FloodEvent  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.user import Role, User  # noqa: E402
from app.services.data_source_health import check_data_source  # noqa: E402

ROLE_DEFS = [
    ("ADMIN", "Full system access: manages users, moderates citizen reports, issues alerts."),
    ("ANALYST", "Reviews model output, issues alerts, moderates citizen reports."),
    ("OPERATOR", "Day-to-day dashboard operation: issues alerts, moderates citizen reports."),
    ("RESEARCHER", "Read access plus data/model-registry visibility for methodology review."),
    ("CITIZEN", "Public account: can submit citizen reports. Default role on self-registration."),
]

DATA_SOURCE_DEFS = [
    dict(
        name="NASA POWER (Daily API)",
        category="weather",
        base_url="https://power.larc.nasa.gov/api/temporal/daily/point",
        description="Daily rainfall/temperature/humidity/wind observations. See docs/DATA-SOURCES.md — "
        "this project's sandbox environment cannot reach this host (egress policy); the code path is real.",
    ),
    dict(
        name="DMMU (Disaster Management & Mitigation Unit, Zambia)",
        category="authoritative-agency",
        base_url="https://www.dmmu.gov.zm",
        description="Zambia's national disaster management authority. Site has been unreachable "
        "(redirect-loop) from this session in prior checks — see docs/DATA-SOURCES.md.",
    ),
    dict(
        name="WARMA (Water Resources Management Authority, Zambia)",
        category="authoritative-agency",
        base_url="https://warma.org.zm",
        description="Zambia's water resources regulator; a candidate cross-check for flood/river data.",
    ),
    dict(
        name="Hand-compiled Zambia flood-event log",
        category="internal",
        base_url="",
        description="ai-engine/data/external/zambia_flood_events_log.csv — 11 sourced events, "
        "compiled from FloodList/UN-SPIDER/Charter reporting. Not a live source; no URL to check.",
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOOD_LOG_CSV = REPO_ROOT / "ai-engine" / "data" / "external" / "zambia_flood_events_log.csv"

LOCATIONS = [
    dict(
        name="Lusaka (city)",
        province="Lusaka",
        latitude=-15.3875,
        longitude=28.3228,
        coordinate_confidence="city-approximate",
        evidence_note=(
            "Provincial capital; named in the governing prompt as a candidate area, "
            "and the location of the January 2023 flood event's Chongwe/Luangwa "
            "district impacts."
        ),
        evidence_source_url="https://www.un-spider.org/advisory-support/emergency-support/13047/floods-zambia",
    ),
    dict(
        name="Kanyama compound, Lusaka",
        province="Lusaka",
        latitude=-15.4415,
        longitude=28.2534,
        coordinate_confidence="city-approximate, not independently geocoded",
        evidence_note=(
            "Independently verified via peer-reviewed/graduate research as a "
            "flood-affected informal settlement (effects on onsite sanitation), "
            "not merely named in the governing prompt."
        ),
        evidence_source_url="https://dspace.unza.zm/items/7e1d043b-57bc-41e8-bda5-cbb85e15b091",
    ),
    dict(
        name="Ng'ombe settlement, Lusaka",
        province="Lusaka",
        latitude=-15.3762,
        longitude=28.3600,
        coordinate_confidence="city-approximate, not independently geocoded",
        evidence_note=(
            "Second candidate location added 2026-09-07 on the strength of "
            "independent academic research documenting urban flooding there."
        ),
        evidence_source_url="https://www.researchgate.net/publication/387084120_Urban_Flooding_A_Case_of_Ng'ombe_Settlement_in_the_City_of_Lusaka_Zambia",
    ),
]


def parse_date(value: str) -> date | None:
    value = value.strip()
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def seed_locations(db) -> int:
    count = 0
    for loc in LOCATIONS:
        existing = db.query(Location).filter_by(name=loc["name"]).one_or_none()
        if existing:
            for k, v in loc.items():
                setattr(existing, k, v)
        else:
            db.add(Location(**loc))
            count += 1
    db.commit()
    return count


def seed_flood_events(db) -> int:
    if not FLOOD_LOG_CSV.exists():
        raise FileNotFoundError(f"Expected real data file not found: {FLOOD_LOG_CSV}")

    count = 0
    with open(FLOOD_LOG_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing = db.query(FloodEvent).filter_by(event_id=row["event_id"]).one_or_none()
            values = dict(
                event_id=row["event_id"],
                start_date=parse_date(row["start_date"]),
                end_date=parse_date(row["end_date"]),
                provinces=row["provinces"],
                districts=row["districts"],
                rivers=row["rivers"],
                impact_note=row["people_or_households_affected"],
                deaths=int(row["deaths"]) if row["deaths"].strip() else None,
                source_name=row["source_name"],
                source_url=row["source_url"],
                confidence_notes=row["confidence_notes"],
            )
            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
            else:
                db.add(FloodEvent(**values))
                count += 1
    db.commit()
    return count


def seed_roles(db) -> int:
    count = 0
    for name, description in ROLE_DEFS:
        existing = db.query(Role).filter_by(name=name).one_or_none()
        if existing:
            existing.description = description
        else:
            db.add(Role(name=name, description=description))
            count += 1
    db.commit()
    return count


def seed_dev_admin(db) -> str:
    password = os.environ.get("FLOODSHIELD_DEV_ADMIN_PASSWORD")
    if not password:
        return "SKIPPED — FLOODSHIELD_DEV_ADMIN_PASSWORD not set in environment."
    admin_role = db.query(Role).filter_by(name="ADMIN").one_or_none()
    if admin_role is None:
        return "SKIPPED — ADMIN role not seeded (seed_roles must run first)."
    existing = db.query(User).filter_by(email="admin@floodshield-zambia.org").one_or_none()
    if existing:
        existing.hashed_password = hash_password(password)
        db.commit()
        return "UPDATED existing dev admin (admin@floodshield-zambia.org) password."
    db.add(
        User(
            email="admin@floodshield-zambia.org",
            hashed_password=hash_password(password),
            full_name="Local Dev Admin",
            role_id=admin_role.id,
            is_active=True,
        )
    )
    db.commit()
    return "CREATED dev admin (admin@floodshield-zambia.org)."


def seed_data_sources(db, do_health_check: bool) -> int:
    count = 0
    for defn in DATA_SOURCE_DEFS:
        existing = db.query(DataSource).filter_by(name=defn["name"]).one_or_none()
        if existing:
            for k, v in defn.items():
                setattr(existing, k, v)
            source = existing
        else:
            source = DataSource(**defn)
            db.add(source)
            count += 1
        db.commit()
        db.refresh(source)
        if do_health_check:
            check_data_source(db, source)
    return count


def main() -> None:
    db = SessionLocal()
    try:
        n_loc = seed_locations(db)
        n_events = seed_flood_events(db)
        n_roles = seed_roles(db)
        admin_result = seed_dev_admin(db)
        n_sources = seed_data_sources(db, do_health_check="--check-sources" in sys.argv)
        print(f"Seeded/updated {len(LOCATIONS)} locations ({n_loc} new).")
        print(f"Seeded/updated flood events from {FLOOD_LOG_CSV.name} ({n_events} new).")
        print(f"Seeded/updated {len(ROLE_DEFS)} roles ({n_roles} new).")
        print(f"Dev admin account: {admin_result}")
        print(f"Seeded/updated {len(DATA_SOURCE_DEFS)} data-source catalog entries ({n_sources} new)."
              + ("" if "--check-sources" in sys.argv else " (pass --check-sources to run live connectivity checks)"))
        print("No weather observations, model versions, or predictions were seeded "
              "(none exist yet - see docs/ROADMAP.md).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
