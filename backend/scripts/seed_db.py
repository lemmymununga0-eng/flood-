"""Seed the database with REAL data only:
- Locations: Lusaka (city-level) plus Kanyama and Ng'ombe, the two settlements this
  project independently verified as flood-affected via peer-reviewed/graduate research
  (see docs/PROJECT-MEMORY.md, 2026-09-07 geographic-scope entry). Coordinates are
  city-approximate, not surveyed — coordinate_confidence reflects that.
- Flood events: the 11 rows in ai-engine/data/external/zambia_flood_events_log.csv,
  loaded verbatim with their source citations.

Nothing here is synthetic. No WeatherObservation, ModelVersion, or Prediction rows are
seeded — those only get populated by a real ingestion run or a real trained model.
Safe to re-run: it upserts by unique key rather than duplicating rows.
"""
import csv
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import Base, SessionLocal, engine  # noqa: E402
from app.models.flood_event import FloodEvent  # noqa: E402
from app.models.location import Location  # noqa: E402

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


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        n_loc = seed_locations(db)
        n_events = seed_flood_events(db)
        print(f"Seeded/updated {len(LOCATIONS)} locations ({n_loc} new).")
        print(f"Seeded/updated flood events from {FLOOD_LOG_CSV.name} ({n_events} new).")
        print("No weather observations, model versions, or predictions were seeded "
              "(none exist yet - see docs/ROADMAP.md).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
